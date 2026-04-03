"""
Категории, магазины и список товаров с фильтрами.
"""
from __future__ import annotations

import logging

from django.db.models import Q, QuerySet
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Category, ProductInfo, Shop
from catalog.serializers import CategorySerializer, ProductInfoSerializer, ShopSerializer

logger: logging.Logger = logging.getLogger("catalog")


class CategoryView(ListAPIView):
    """Список всех категорий."""

    queryset: QuerySet[Category] = Category.objects.all()
    serializer_class: type[CategorySerializer] = CategorySerializer


class ShopView(ListAPIView):
    """Список магазинов, которые сейчас принимают заказы."""

    queryset: QuerySet[Shop] = Shop.objects.filter(state=True)
    serializer_class: type[ShopSerializer] = ShopSerializer


class ProductInfoView(APIView):
    """Каталог предложений ProductInfo с фильтрами shop_id и category_id."""

    def get(self, request: Request, *args: object, **kwargs: object) -> Response:
        query: Q = Q(shop__state=True)
        shop_id: str | None = request.query_params.get("shop_id")
        category_id: str | None = request.query_params.get("category_id")
        if shop_id:
            query &= Q(shop_id=shop_id)
        if category_id:
            query &= Q(product__category_id=category_id)

        queryset: QuerySet[ProductInfo] = (
            ProductInfo.objects.filter(query)
            .select_related("shop", "product__category")
            .prefetch_related("product_parameters__parameter")
            .distinct()
        )

        serializer = ProductInfoSerializer(queryset, many=True)
        logger.debug(
            "Выдача каталога: фильтры shop_id=%s category_id=%s, записей=%s",
            shop_id,
            category_id,
            queryset.count(),
            extra={"caller_class": "ProductInfoView", "caller_def": "get"},
        )
        return Response(serializer.data)
