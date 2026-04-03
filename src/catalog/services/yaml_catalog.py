"""
Загрузка и разбор YAML-прайса партнёра в модели каталога.

Используется синхронно в API и из фоновой задачи Celery (do_import).
"""
from __future__ import annotations

import logging
from io import BytesIO
from typing import Any, BinaryIO

import requests
from django.db import transaction
from yaml import Loader, load as load_yaml

from catalog.models import Category, Parameter, Product, ProductInfo, ProductParameter, Shop

logger: logging.Logger = logging.getLogger("catalog")


def load_yaml_document(stream: BinaryIO) -> dict[str, Any]:
    """Парсит YAML в словарь Python; ожидается структура с ключами shop, categories, goods."""
    data: Any = load_yaml(stream, Loader=Loader)
    if not isinstance(data, dict):
        raise ValueError("Корень YAML должен быть объектом")
    return data


@transaction.atomic
def import_price_from_mapping(data: dict[str, Any], shop_user_id: int) -> Shop:
    """
    Применяет распарсенные данные прайса к БД для магазина, привязанного к пользователю.

    Логика соответствует учебному примеру: категории по id из файла, полная замена ProductInfo
    для данного магазина перед вставкой новых строк.
    """
    shop_name: str = str(data["shop"])
    shop, _ = Shop.objects.get_or_create(name=shop_name, defaults={"user_id": shop_user_id})
    if shop.user_id != shop_user_id:
        shop.user_id = shop_user_id
        shop.save(update_fields=["user_id"])

    categories_raw: list[Any] = data.get("categories") or []
    for category in categories_raw:
        category_object, _ = Category.objects.get_or_create(
            id=int(category["id"]),
            defaults={"name": category["name"]},
        )
        if category_object.name != category["name"]:
            category_object.name = category["name"]
            category_object.save(update_fields=["name"])
        category_object.shops.add(shop.id)

    ProductInfo.objects.filter(shop_id=shop.id).delete()

    goods_raw: list[Any] = data.get("goods") or []
    for item in goods_raw:
        product, _ = Product.objects.get_or_create(
            name=item["name"],
            category_id=int(item["category"]),
        )
        product_info: ProductInfo = ProductInfo.objects.create(
            product_id=product.id,
            external_id=int(item["id"]),
            model=item.get("model") or "",
            price=int(item["price"]),
            price_rrc=int(item["price_rrc"]),
            quantity=int(item["quantity"]),
            shop_id=shop.id,
        )
        parameters: dict[str, Any] = item.get("parameters") or {}
        for name, value in parameters.items():
            parameter_object, _ = Parameter.objects.get_or_create(name=str(name))
            ProductParameter.objects.create(
                product_info_id=product_info.id,
                parameter_id=parameter_object.id,
                value=str(value),
            )

    logger.info(
        "Импорт прайса завершён для магазина %s",
        shop.name,
        extra={"caller_class": "yaml_catalog", "caller_def": "import_price_from_mapping"},
    )
    return shop


def import_price_from_url(url: str, shop_user_id: int) -> Shop:
    """Скачивает YAML по HTTP и импортирует его содержимое."""
    response: requests.Response = requests.get(url, timeout=60)
    response.raise_for_status()
    return import_price_from_bytes(response.content, shop_user_id)


def import_price_from_bytes(content: bytes, shop_user_id: int) -> Shop:
    """Импортирует прайс из байтов YAML (удобно для тестов и загрузки из файла)."""
    with BytesIO(content) as buf:
        data: dict[str, Any] = load_yaml_document(buf)
    return import_price_from_mapping(data, shop_user_id)
