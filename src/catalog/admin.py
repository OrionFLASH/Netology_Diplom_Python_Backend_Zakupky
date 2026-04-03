"""
Настройка админ-панели: заказы с быстрым изменением статуса, справочники каталога.
"""
from __future__ import annotations

from django.contrib import admin

from catalog.models import (
    Category,
    ConfirmEmailToken,
    Contact,
    Order,
    OrderItem,
    Parameter,
    Product,
    ProductInfo,
    ProductParameter,
    Shop,
    User,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Список пользователей: email как логин, тип учётной записи, права доступа."""

    ordering: tuple[str, ...] = ("email",)
    list_display: tuple[str, ...] = ("email", "first_name", "last_name", "type", "is_staff", "is_active")
    search_fields: tuple[str, ...] = ("email", "first_name", "last_name", "company")
    list_filter: tuple[str, ...] = ("type", "is_staff", "is_active")
    fieldsets: tuple[tuple[str | None, dict[str, tuple[str, ...]]], ...] = (
        (None, {"fields": ("email", "password")}),
        ("Персональные данные", {"fields": ("first_name", "last_name", "username", "company", "position")}),
        ("Тип", {"fields": ("type",)}),
        ("Права", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )
    filter_horizontal: tuple[str, ...] = ("groups", "user_permissions")


class OrderItemInline(admin.TabularInline):
    """Позиции заказа внутри карточки заказа."""

    model: type[OrderItem] = OrderItem
    extra: int = 0
    raw_id_fields: tuple[str, ...] = ("product_info",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Просмотр заказов и смена статуса из списка.

    При сохранении модели срабатывают сигналы и отправляется email клиенту (если статус изменился).
    """

    list_display: tuple[str, ...] = ("id", "user", "dt", "state", "contact")
    list_filter: tuple[str, ...] = ("state",)
    search_fields: tuple[str, ...] = ("user__email",)
    list_editable: tuple[str, ...] = ("state",)
    inlines: tuple[type[admin.TabularInline], ...] = (OrderItemInline,)
    raw_id_fields: tuple[str, ...] = ("user", "contact")


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = ("name", "state", "user")
    search_fields: tuple[str, ...] = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    filter_horizontal: tuple[str, ...] = ("shops",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = ("name", "category")
    search_fields: tuple[str, ...] = ("name",)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = ("product", "shop", "price", "quantity", "external_id")
    list_filter: tuple[str, ...] = ("shop",)
    search_fields: tuple[str, ...] = ("product__name", "model")


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    search_fields: tuple[str, ...] = ("name",)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = ("product_info", "parameter", "value")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = ("user", "city", "street", "phone")
    search_fields: tuple[str, ...] = ("city", "street", "user__email")


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = ("user", "created_at", "key")
    search_fields: tuple[str, ...] = ("user__email", "key")
