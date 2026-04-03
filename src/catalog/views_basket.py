"""
Корзина покупателя: одна запись Order со статусом basket на пользователя.
"""
from __future__ import annotations

import logging

from django.db import IntegrityError
from django.db.models import F, IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from ujson import loads as load_json
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Order, OrderItem, OrderState
from catalog.privacy import mask_user_id
from catalog.serializers import OrderItemSerializer, OrderSerializer

logger: logging.Logger = logging.getLogger("catalog")


class BasketView(APIView):
    """Просмотр корзины и изменение состава через items (JSON-строка, как в учебном API)."""

    def get(self, request: Request, *args: object, **kwargs: object) -> JsonResponse | Response:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        basket = (
            Order.objects.filter(user_id=request.user.id, state=OrderState.BASKET)
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .annotate(
                total_sum=Coalesce(
                    Sum(F("ordered_items__quantity") * F("ordered_items__product_info__price")),
                    Value(0),
                    output_field=IntegerField(),
                )
            )
            .distinct()
        )
        serializer = OrderSerializer(basket, many=True)
        logger.debug(
            "Просмотр корзины пользователя %s",
            mask_user_id(request.user.id),
            extra={"caller_class": "BasketView", "caller_def": "get"},
        )
        return Response(serializer.data)

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        items_string: str | None = request.data.get("items")
        if not items_string:
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        try:
            items_dict: list[dict[str, object]] = load_json(items_string)
        except ValueError:
            return JsonResponse({"Status": False, "Errors": "Неверный формат запроса"})

        basket, _ = Order.objects.get_or_create(user_id=request.user.id, state=OrderState.BASKET)
        objects_created: int = 0
        for order_item in items_dict:
            payload: dict[str, object] = {**order_item, "order": basket.id}
            serializer = OrderItemSerializer(data=payload)
            if not serializer.is_valid():
                return JsonResponse({"Status": False, "Errors": serializer.errors})
            try:
                serializer.save()
            except IntegrityError as error:
                return JsonResponse({"Status": False, "Errors": str(error)})
            objects_created += 1

        logger.info(
            "В корзину добавлено позиций: %s (user=%s)",
            objects_created,
            mask_user_id(request.user.id),
            extra={"caller_class": "BasketView", "caller_def": "post"},
        )
        return JsonResponse({"Status": True, "Создано объектов": objects_created})

    def delete(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        items_string: str | None = request.data.get("items")
        if not items_string:
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        items_list: list[str] = items_string.split(",")
        basket, _ = Order.objects.get_or_create(user_id=request.user.id, state=OrderState.BASKET)
        query: Q = Q()
        objects_deleted: bool = False
        for order_item_id in items_list:
            if order_item_id.strip().isdigit():
                query |= Q(order_id=basket.id, id=int(order_item_id))
                objects_deleted = True

        if objects_deleted:
            deleted_count: int = OrderItem.objects.filter(query).delete()[0]
            return JsonResponse({"Status": True, "Удалено объектов": deleted_count})
        return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

    def put(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        items_string: str | None = request.data.get("items")
        if not items_string:
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        try:
            items_dict: list[dict[str, object]] = load_json(items_string)
        except ValueError:
            return JsonResponse({"Status": False, "Errors": "Неверный формат запроса"})

        basket, _ = Order.objects.get_or_create(user_id=request.user.id, state=OrderState.BASKET)
        objects_updated: int = 0
        for order_item in items_dict:
            oid = order_item.get("id")
            qty = order_item.get("quantity")
            if isinstance(oid, int) and isinstance(qty, int):
                objects_updated += OrderItem.objects.filter(order_id=basket.id, id=oid).update(quantity=qty)

        return JsonResponse({"Status": True, "Обновлено объектов": objects_updated})
