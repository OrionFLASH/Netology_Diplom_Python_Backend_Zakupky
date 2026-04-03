"""
Заказы покупателя: список, детальная запись, подтверждение из корзины, смена статуса (для персонала).
"""
from __future__ import annotations

import logging

from django.db import IntegrityError
from django.db.models import F, IntegerField, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Order, OrderState
from catalog.privacy import mask_user_id
from catalog.serializers import OrderSerializer

logger: logging.Logger = logging.getLogger("catalog")


class OrderView(APIView):
    """Операции с заказами текущего пользователя и административное изменение статуса."""

    def get(self, request: Request, *args: object, **kwargs: object) -> JsonResponse | Response:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        orders = (
            Order.objects.filter(user_id=request.user.id)
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

        order_id: str | None = request.query_params.get("id")
        if order_id and order_id.isdigit():
            orders = orders.filter(id=int(order_id))

        serializer = OrderSerializer(orders, many=True)
        logger.debug(
            "Список заказов пользователя %s, отфильтровано по id=%s",
            mask_user_id(request.user.id),
            order_id,
            extra={"caller_class": "OrderView", "caller_def": "get"},
        )
        return Response(serializer.data)

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        if not {"id", "contact"}.issubset(request.data):
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        basket_id: str = str(request.data["id"])
        if not basket_id.isdigit():
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        order: Order | None = Order.objects.filter(
            user_id=request.user.id,
            id=int(basket_id),
            state=OrderState.BASKET,
        ).first()
        if order is None:
            return JsonResponse({"Status": False, "Errors": "Корзина не найдена"})

        order.contact_id = int(request.data["contact"])
        order.state = OrderState.NEW
        try:
            order.save()
        except IntegrityError:
            return JsonResponse({"Status": False, "Errors": "Неправильно указаны аргументы"})

        logger.info(
            "Заказ #%s подтверждён пользователем %s",
            order.id,
            mask_user_id(request.user.id),
            extra={"caller_class": "OrderView", "caller_def": "post"},
        )
        return JsonResponse({"Status": True})

    def put(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        """
        Изменение статуса заказа — только для сотрудников (is_staff).

        Тело запроса: id заказа, state — одно из значений OrderState (кроме корзины).
        """
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({"Status": False, "Error": "Только для персонала"}, status=403)

        if not {"id", "state"}.issubset(request.data):
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        oid: str = str(request.data["id"])
        if not oid.isdigit():
            return JsonResponse({"Status": False, "Errors": "Некорректный идентификатор заказа"})

        new_state: str = str(request.data["state"])
        allowed: set[str] = {s for s, _ in OrderState.choices if s != OrderState.BASKET}
        if new_state not in allowed:
            return JsonResponse({"Status": False, "Errors": "Недопустимый статус"})

        order_obj: Order | None = Order.objects.filter(id=int(oid)).exclude(state=OrderState.BASKET).first()
        if order_obj is None:
            return JsonResponse({"Status": False, "Errors": "Заказ не найден"})

        order_obj.state = new_state
        order_obj.save(update_fields=["state"])

        logger.info(
            "Статус заказа #%s изменён персоналом на %s",
            oid,
            new_state,
            extra={"caller_class": "OrderView", "caller_def": "put"},
        )
        return JsonResponse({"Status": True})
