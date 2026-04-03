"""
Экспорт каталога магазина в YAML (продвинутая часть задания).

Формат согласован с файлом импорта: shop, categories, goods с parameters.
"""
from __future__ import annotations

from typing import Any

import yaml

from catalog.models import Category, ProductInfo, Shop


def build_shop_catalog_document(shop: Shop) -> dict[str, Any]:
    """Формирует словарь прайса по данным БД для указанного магазина."""
    categories_qs = Category.objects.filter(shops=shop).distinct().order_by("id")
    categories: list[dict[str, Any]] = [{"id": c.id, "name": c.name} for c in categories_qs]

    goods: list[dict[str, Any]] = []
    for info in (
        ProductInfo.objects.filter(shop=shop)
        .select_related("product")
        .prefetch_related("product_parameters__parameter")
        .order_by("id")
    ):
        params: dict[str, Any] = {
            pp.parameter.name: pp.value for pp in info.product_parameters.all()
        }
        goods.append(
            {
                "id": int(info.external_id),
                "category": int(info.product.category_id) if info.product.category_id else None,
                "model": info.model or "",
                "name": info.product.name,
                "price": int(info.price),
                "price_rrc": int(info.price_rrc),
                "quantity": int(info.quantity),
                "parameters": params,
            }
        )

    return {
        "shop": shop.name,
        "categories": categories,
        "goods": goods,
    }


def dump_shop_catalog_yaml(shop: Shop) -> bytes:
    """Сериализует каталог в YAML (UTF-8)."""
    document: dict[str, Any] = build_shop_catalog_document(shop)
    text: str = yaml.safe_dump(
        document,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    return text.encode("utf-8")
