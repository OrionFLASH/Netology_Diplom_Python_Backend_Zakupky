"""
Сериализаторы DRF для пользователей, каталога, корзины и заказов.

Поля ответов по возможности совместимы с учебным примером Netology; добавлены описание товара и ФИО контакта.
"""
from __future__ import annotations

from rest_framework import serializers

from catalog.models import (
    Category,
    Contact,
    Order,
    OrderItem,
    Product,
    ProductInfo,
    ProductParameter,
    Shop,
    User,
)


class ContactSerializer(serializers.ModelSerializer):
    """Контакт доставки; user передаётся на запись только из представления."""

    class Meta:
        model: type[Contact] = Contact
        fields: tuple[str, ...] = (
            "id",
            "first_name",
            "last_name",
            "patronymic",
            "contact_email",
            "city",
            "street",
            "house",
            "structure",
            "building",
            "apartment",
            "phone",
            "user",
        )
        read_only_fields: tuple[str, ...] = ("id",)
        extra_kwargs: dict[str, dict[str, bool]] = {"user": {"write_only": True}}


class UserSerializer(serializers.ModelSerializer):
    """Профиль пользователя с вложенными контактами (только чтение)."""

    contacts: ContactSerializer = ContactSerializer(read_only=True, many=True)

    class Meta:
        model: type[User] = User
        fields: tuple[str, ...] = (
            "id",
            "first_name",
            "last_name",
            "email",
            "company",
            "position",
            "contacts",
        )
        read_only_fields: tuple[str, ...] = ("id",)


class CategorySerializer(serializers.ModelSerializer):
    """Список категорий каталога."""

    class Meta:
        model: type[Category] = Category
        fields: tuple[str, ...] = ("id", "name")
        read_only_fields: tuple[str, ...] = ("id",)


class ShopSerializer(serializers.ModelSerializer):
    """Краткие сведения о магазине (в т.ч. флаг приёма заказов)."""

    class Meta:
        model: type[Shop] = Shop
        fields: tuple[str, ...] = ("id", "name", "state")
        read_only_fields: tuple[str, ...] = ("id",)


class ProductSerializer(serializers.ModelSerializer):
    """Базовая информация о номенклатуре в составе предложения."""

    category: serializers.StringRelatedField = serializers.StringRelatedField()

    class Meta:
        model: type[Product] = Product
        fields: tuple[str, ...] = ("name", "category", "description")


class ProductParameterSerializer(serializers.ModelSerializer):
    """Пара «имя — значение» для карточки товара."""

    parameter: serializers.StringRelatedField = serializers.StringRelatedField()

    class Meta:
        model: type[ProductParameter] = ProductParameter
        fields: tuple[str, ...] = ("parameter", "value")


class ProductInfoSerializer(serializers.ModelSerializer):
    """
    Предложение в каталоге: цена, остаток, магазин, характеристики.
    Поле supplier дублирует название магазина для наглядности в JSON.
    """

    product: ProductSerializer = ProductSerializer(read_only=True)
    product_parameters: ProductParameterSerializer = ProductParameterSerializer(read_only=True, many=True)
    supplier: serializers.CharField = serializers.CharField(source="shop.name", read_only=True)

    class Meta:
        model: type[ProductInfo] = ProductInfo
        fields: tuple[str, ...] = (
            "id",
            "model",
            "product",
            "shop",
            "supplier",
            "quantity",
            "price",
            "price_rrc",
            "product_parameters",
        )
        read_only_fields: tuple[str, ...] = ("id",)


class OrderItemSerializer(serializers.ModelSerializer):
    """Позиция заказа при создании из JSON (order подставляется программно)."""

    class Meta:
        model: type[OrderItem] = OrderItem
        fields: tuple[str, ...] = ("id", "product_info", "quantity", "order")
        read_only_fields: tuple[str, ...] = ("id",)
        extra_kwargs: dict[str, dict[str, bool]] = {"order": {"write_only": True}}


class OrderItemReadSerializer(OrderItemSerializer):
    """Позиция с развёрнутым product_info для ответов GET."""

    product_info: ProductInfoSerializer = ProductInfoSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    """
    Заказ с позициями и суммой.

    total_sum ожидается от аннотации queryset (Sum(quantity * price)); без аннотации будет ошибка —
    представления всегда добавляют annotate.
    """

    ordered_items: OrderItemReadSerializer = OrderItemReadSerializer(read_only=True, many=True)
    total_sum: serializers.IntegerField = serializers.IntegerField()
    contact: ContactSerializer = ContactSerializer(read_only=True)

    class Meta:
        model: type[Order] = Order
        fields: tuple[str, ...] = ("id", "ordered_items", "state", "dt", "total_sum", "contact")
        read_only_fields: tuple[str, ...] = ("id",)
