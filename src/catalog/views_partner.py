"""
API для магазинов-партнёров: загрузка прайса, статус приёма заказов, список заказов по товарам магазина, экспорт каталога.

Дополнительно: запуск фонового импорта для администратора (интеграция с Celery).
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import F, IntegerField, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Order, OrderState, Shop, UserType
from catalog.privacy import mask_user_id
from catalog.serializers import OrderSerializer, ShopSerializer
from catalog.services.yaml_catalog import import_price_from_url
from catalog.services.yaml_export import dump_shop_catalog_yaml

logger: logging.Logger = logging.getLogger("catalog")


def _parse_bool(value: str) -> bool:
    """Преобразует строковое значение из формы в bool (совместимо с учебным API)."""
    normalized: str = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError("Некорректное логическое значение")


class PartnerUpdate(APIView):
    """Обновление прайса магазина по URL с YAML (только пользователи типа shop)."""

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)
        if request.user.type != UserType.SHOP:
            return JsonResponse({"Status": False, "Error": "Только для магазинов"}, status=403)

        url: str | None = request.data.get("url")
        if not url:
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as error:
            return JsonResponse({"Status": False, "Error": str(error)})

        try:
            import_price_from_url(url, int(request.user.id))
        except Exception as exc:  # noqa: BLE001 — отдаём понятную ошибку клиенту
            logger.exception("Ошибка импорта прайса")
            return JsonResponse({"Status": False, "Errors": str(exc)})

        logger.info(
            "Партнёр %s обновил прайс по ссылке",
            mask_user_id(int(request.user.id)),
            extra={"caller_class": "PartnerUpdate", "caller_def": "post"},
        )
        return JsonResponse({"Status": True})


class PartnerState(APIView):
    """Просмотр и переключение флага приёма заказов магазином."""

    def get(self, request: Request, *args: object, **kwargs: object) -> JsonResponse | Response:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)
        if request.user.type != UserType.SHOP:
            return JsonResponse({"Status": False, "Error": "Только для магазинов"}, status=403)

        shop: Shop | None = Shop.objects.filter(user_id=request.user.id).first()
        if shop is None:
            return JsonResponse({"Status": False, "Errors": "Магазин не найден"}, status=404)
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)
        if request.user.type != UserType.SHOP:
            return JsonResponse({"Status": False, "Error": "Только для магазинов"}, status=403)

        state_raw: str | None = request.data.get("state")
        if state_raw is None:
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})
        try:
            new_state: bool = _parse_bool(str(state_raw))
        except ValueError as error:
            return JsonResponse({"Status": False, "Errors": str(error)})

        Shop.objects.filter(user_id=request.user.id).update(state=new_state)
        return JsonResponse({"Status": True})


class PartnerOrders(APIView):
    """Заказы, в которых есть товары данного магазина (кроме корзин)."""

    def get(self, request: Request, *args: object, **kwargs: object) -> JsonResponse | Response:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)
        if request.user.type != UserType.SHOP:
            return JsonResponse({"Status": False, "Error": "Только для магазинов"}, status=403)

        orders = (
            Order.objects.filter(ordered_items__product_info__shop__user_id=request.user.id)
            .exclude(state=OrderState.BASKET)
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .select_related("contact")
            .annotate(
                total_sum=Coalesce(
                    Sum(F("ordered_items__quantity") * F("ordered_items__product_info__price")),
                    Value(0),
                    output_field=IntegerField(),
                )
            )
            .distinct()
        )
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class PartnerExportView(APIView):
    """Экспорт актуального каталога магазина в YAML."""

    def get(self, request: Request, *args: object, **kwargs: object) -> HttpResponse | JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)
        if request.user.type != UserType.SHOP:
            return JsonResponse({"Status": False, "Error": "Только для магазинов"}, status=403)

        shop: Shop | None = Shop.objects.filter(user_id=request.user.id).first()
        if shop is None:
            return JsonResponse({"Status": False, "Errors": "Магазин не найден — сначала загрузите прайс"})

        payload: bytes = dump_shop_catalog_yaml(shop)
        filename: str = f"catalog_{shop.id}.yaml"
        response = HttpResponse(payload, content_type="application/x-yaml; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        logger.info(
            "Экспорт каталога магазина %s",
            shop.id,
            extra={"caller_class": "PartnerExportView", "caller_def": "get"},
        )
        return response


class AdminImportTaskView(APIView):
    """
    Постановка задачи импорта в Celery (для проверки продвинутой части).

    Доступно только администраторам сайта; указывается URL и пользователь-магазин.
    """

    permission_classes: list[type[IsAdminUser]] = [IsAdminUser]

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        url: str | None = request.data.get("url")
        shop_user_id_raw = request.data.get("shop_user_id")
        if not url or shop_user_id_raw is None:
            return JsonResponse({"Status": False, "Errors": "Нужны поля url и shop_user_id"})

        try:
            shop_user_id: int = int(shop_user_id_raw)
        except (TypeError, ValueError):
            return JsonResponse({"Status": False, "Errors": "shop_user_id должен быть числом"})

        from catalog.tasks import do_import_task

        async_result = do_import_task.delay(url, shop_user_id)
        logger.info(
            "Поставлена задача импорта Celery task_id=%s для пользователя %s",
            async_result.id,
            shop_user_id,
            extra={"caller_class": "AdminImportTaskView", "caller_def": "post"},
        )
        return JsonResponse({"Status": True, "task_id": async_result.id})
