"""
Сквозной сценарий: регистрация, подтверждение, вход, импорт прайса, корзина, контакт, заказ.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core import mail
from rest_framework.test import APIClient

from catalog.models import ConfirmEmailToken, OrderState, User, UserType
from catalog.services.yaml_catalog import import_price_from_bytes


@pytest.mark.django_db
def test_buyer_registration_login_and_order() -> None:
    client: APIClient = APIClient()
    base: str = "/api/v1"

    reg_payload: dict[str, str] = {
        "first_name": "Иван",
        "last_name": "Покупатель",
        "email": "buyer@example.com",
        "password": "ComplexPass123!",
        "company": "ООО Рога",
        "position": "Менеджер",
    }
    response = client.post(f"{base}/user/register", reg_payload, format="json")
    assert response.status_code == 200
    assert response.json()["Status"] is True

    user: User = User.objects.get(email="buyer@example.com")
    assert user.is_active is False
    token: ConfirmEmailToken = ConfirmEmailToken.objects.get(user=user)

    confirm = client.post(
        f"{base}/user/register/confirm",
        {"email": user.email, "token": token.key},
        format="json",
    )
    assert confirm.status_code == 200
    user.refresh_from_db()
    assert user.is_active is True

    login = client.post(
        f"{base}/user/login",
        {"email": user.email, "password": reg_payload["password"]},
        format="json",
    )
    assert login.status_code == 200
    auth_token: str = login.json()["Token"]
    client.credentials(HTTP_AUTHORIZATION=f"Token {auth_token}")

    shop_user: User = User.objects.create_user(
        email="shop@example.com",
        password="ShopPass123!!",
        first_name="Маг",
        last_name="Азин",
        type=UserType.SHOP,
        is_active=True,
    )
    yaml_path: Path = Path(__file__).resolve().parents[2] / "data" / "shop1.yaml"
    raw: bytes = yaml_path.read_bytes()
    import_price_from_bytes(raw, int(shop_user.id))

    from catalog.models import ProductInfo

    pi: ProductInfo = ProductInfo.objects.first()
    assert pi is not None

    items_json: str = json.dumps([{"product_info": pi.id, "quantity": 1}])
    basket_post = client.post(f"{base}/basket", {"items": items_json}, format="json")
    assert basket_post.status_code == 200
    assert basket_post.json()["Status"] is True

    contact = client.post(
        f"{base}/user/contact",
        {
            "city": "Москва",
            "street": "Тверская",
            "house": "1",
            "phone": "+79990000000",
        },
        format="json",
    )
    assert contact.status_code == 200
    contact_id: int = user.contacts.first().id  # type: ignore[union-attr]

    basket_id = user.orders.get(state=OrderState.BASKET).id
    mail.outbox.clear()
    order_post = client.post(
        f"{base}/order",
        {"id": str(basket_id), "contact": str(contact_id)},
        format="json",
    )
    assert order_post.status_code == 200
    assert order_post.json()["Status"] is True
    assert len(mail.outbox) >= 1

    orders = client.get(f"{base}/order")
    assert orders.status_code == 200
    payload = orders.json()
    assert isinstance(payload, list)
    assert any(row["state"] == OrderState.NEW for row in payload)


@pytest.mark.django_db
def test_basket_accepts_items_as_json_array() -> None:
    """
    Поле items в POST /basket может быть не только JSON-строкой (учебный вариант),
    но и массивом в теле application/json (типичные HTTP-клиенты).
    """
    client = APIClient()
    base = "/api/v1"
    shop_user = User.objects.create_user(
        email="shop2@example.com",
        password="ShopPass123!!",
        first_name="М",
        last_name="С",
        type=UserType.SHOP,
        is_active=True,
    )
    yaml_path = Path(__file__).resolve().parents[2] / "data" / "shop1.yaml"
    import_price_from_bytes(yaml_path.read_bytes(), int(shop_user.id))

    from catalog.models import ProductInfo

    pi = ProductInfo.objects.first()
    assert pi is not None

    buyer = User.objects.create_user(
        email="buyer2@example.com",
        password="ComplexPass123!",
        first_name="П",
        last_name="К",
        type=UserType.BUYER,
        is_active=True,
    )
    login = client.post(
        base + "/user/login",
        {"email": buyer.email, "password": "ComplexPass123!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Token {login.json()['Token']}")

    response = client.post(
        base + "/basket",
        {"items": [{"product_info": pi.id, "quantity": 2}]},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["Status"] is True
