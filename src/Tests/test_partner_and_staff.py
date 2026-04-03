"""
Автотесты партнёрского API, админского Celery-импорта и смены статуса заказа персоналом (PUT /order).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from catalog.models import ConfirmEmailToken, Order, OrderState, Shop, User, UserType
from catalog.services.yaml_catalog import import_price_from_bytes


@pytest.mark.django_db
def test_partner_state_export_orders_and_update() -> None:
    """
    Магазин: GET state/export/orders, оформление заказа покупателем → заказ в partner/orders,
    POST state, POST update (импорт по URL с заглушкой сети).
    """
    client: APIClient = APIClient()
    base: str = "/api/v1"
    yaml_path: Path = Path(__file__).resolve().parents[2] / "data" / "shop1.yaml"

    shop_user: User = User.objects.create_user(
        email="partner_shop@example.com",
        password="ShopPass123!!",
        first_name="П",
        last_name="М",
        type=UserType.SHOP,
        is_active=True,
    )
    import_price_from_bytes(yaml_path.read_bytes(), int(shop_user.id))

    shop_login = client.post(
        f"{base}/user/login",
        {"email": shop_user.email, "password": "ShopPass123!!"},
        format="json",
    )
    assert shop_login.status_code == 200
    shop_token: str = shop_login.json()["Token"]
    client.credentials(HTTP_AUTHORIZATION=f"Token {shop_token}")

    state_resp = client.get(f"{base}/partner/state")
    assert state_resp.status_code == 200
    state_payload: dict[str, object] = state_resp.json()
    assert "state" in state_payload and "name" in state_payload
    assert state_payload["state"] is True

    export_resp = client.get(f"{base}/partner/export")
    assert export_resp.status_code == 200
    assert b"shop:" in export_resp.content

    orders_empty = client.get(f"{base}/partner/orders")
    assert orders_empty.status_code == 200
    assert orders_empty.json() == []

    # Регистрация и активация покупателя (как в основном сценарии)
    reg_payload: dict[str, str] = {
        "first_name": "Покуп",
        "last_name": "Атель",
        "email": "partner_buyer@example.com",
        "password": "ComplexPass123!",
        "company": "ООО Тест",
        "position": "Закупщик",
    }
    assert client.post(f"{base}/user/register", reg_payload, format="json").status_code == 200
    buyer: User = User.objects.get(email="partner_buyer@example.com")
    token_obj: ConfirmEmailToken = ConfirmEmailToken.objects.get(user=buyer)
    assert (
        client.post(
            f"{base}/user/register/confirm",
            {"email": buyer.email, "token": token_obj.key},
            format="json",
        ).status_code
        == 200
    )

    buyer_login = client.post(
        f"{base}/user/login",
        {"email": buyer.email, "password": reg_payload["password"]},
        format="json",
    )
    buyer_token: str = buyer_login.json()["Token"]
    client.credentials(HTTP_AUTHORIZATION=f"Token {buyer_token}")

    from catalog.models import ProductInfo

    pi: ProductInfo = ProductInfo.objects.first()
    assert pi is not None
    basket_post = client.post(
        f"{base}/basket",
        {"items": json.dumps([{"product_info": pi.id, "quantity": 1}])},
        format="json",
    )
    assert basket_post.status_code == 200

    assert (
        client.post(
            f"{base}/user/contact",
            {
                "city": "СПб",
                "street": "Невский",
                "house": "1",
                "phone": "+79990001122",
            },
            format="json",
        ).status_code
        == 200
    )
    contact_id: int = buyer.contacts.first().id  # type: ignore[union-attr]
    basket_id: int = buyer.orders.get(state=OrderState.BASKET).id

    assert (
        client.post(
            f"{base}/order",
            {"id": str(basket_id), "contact": str(contact_id)},
            format="json",
        ).status_code
        == 200
    )

    client.credentials(HTTP_AUTHORIZATION=f"Token {shop_token}")
    orders_after = client.get(f"{base}/partner/orders")
    assert orders_after.status_code == 200
    partner_orders: list[dict[str, object]] = orders_after.json()
    assert len(partner_orders) == 1
    assert partner_orders[0]["state"] == OrderState.NEW

    toggle = client.post(f"{base}/partner/state", {"state": "false"}, format="json")
    assert toggle.status_code == 200
    assert toggle.json()["Status"] is True
    assert Shop.objects.get(user_id=shop_user.id).state is False

    shop_row: Shop = Shop.objects.get(user_id=shop_user.id)
    with patch("catalog.views_partner.import_price_from_url", return_value=shop_row) as mocked_import:
        upd = client.post(
            f"{base}/partner/update",
            {"url": "https://example.com/catalog.yaml"},
            format="json",
        )
    assert upd.status_code == 200
    assert upd.json()["Status"] is True
    mocked_import.assert_called_once_with("https://example.com/catalog.yaml", int(shop_user.id))


@pytest.mark.django_db
def test_staff_put_order_status_and_buyer_forbidden() -> None:
    """Персонал меняет статус заказа через PUT /order; покупатель получает 403."""
    client: APIClient = APIClient()
    base: str = "/api/v1"
    yaml_path: Path = Path(__file__).resolve().parents[2] / "data" / "shop1.yaml"

    shop_user: User = User.objects.create_user(
        email="staffflow_shop@example.com",
        password="ShopPass123!!",
        first_name="С",
        last_name="М",
        type=UserType.SHOP,
        is_active=True,
    )
    import_price_from_bytes(yaml_path.read_bytes(), int(shop_user.id))

    staff_user: User = User.objects.create_user(
        email="staff@example.com",
        password="StaffPass123!!",
        first_name="А",
        last_name="Д",
        type=UserType.BUYER,
        is_active=True,
        is_staff=True,
    )

    reg_payload: dict[str, str] = {
        "first_name": "Б",
        "last_name": "П",
        "email": "staffflow_buyer@example.com",
        "password": "ComplexPass123!",
        "company": "ООО",
        "position": "М",
    }
    assert client.post(f"{base}/user/register", reg_payload, format="json").status_code == 200
    buyer: User = User.objects.get(email="staffflow_buyer@example.com")
    confirm_key: str = ConfirmEmailToken.objects.get(user=buyer).key
    assert (
        client.post(
            f"{base}/user/register/confirm",
            {"email": buyer.email, "token": confirm_key},
            format="json",
        ).status_code
        == 200
    )

    buyer_login = client.post(
        f"{base}/user/login",
        {"email": buyer.email, "password": reg_payload["password"]},
        format="json",
    )
    buyer_token: str = buyer_login.json()["Token"]
    client.credentials(HTTP_AUTHORIZATION=f"Token {buyer_token}")

    from catalog.models import ProductInfo

    pi = ProductInfo.objects.first()
    assert pi is not None
    assert (
        client.post(
            f"{base}/basket",
            {"items": [{"product_info": pi.id, "quantity": 1}]},
            format="json",
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"{base}/user/contact",
            {"city": "Мск", "street": "Ленина", "phone": "+79993334455"},
            format="json",
        ).status_code
        == 200
    )
    cid: int = buyer.contacts.first().id  # type: ignore[union-attr]
    bid: int = buyer.orders.get(state=OrderState.BASKET).id
    assert client.post(f"{base}/order", {"id": str(bid), "contact": str(cid)}, format="json").status_code == 200

    order: Order = buyer.orders.get(state=OrderState.NEW)
    order_id: int = order.id

    # Покупатель не может менять статус
    put_buyer = client.put(
        f"{base}/order",
        {"id": str(order_id), "state": OrderState.CONFIRMED},
        format="json",
    )
    assert put_buyer.status_code == 403

    staff_login = client.post(
        f"{base}/user/login",
        {"email": staff_user.email, "password": "StaffPass123!!"},
        format="json",
    )
    assert staff_login.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Token {staff_login.json()['Token']}")

    put_staff = client.put(
        f"{base}/order",
        {"id": str(order_id), "state": OrderState.CONFIRMED},
        format="json",
    )
    assert put_staff.status_code == 200
    assert put_staff.json()["Status"] is True
    order.refresh_from_db()
    assert order.state == OrderState.CONFIRMED


@pytest.mark.django_db
def test_admin_import_task_eager_runs_import() -> None:
    """
    POST /admin/import_task под staff: Celery в тестах eager — задача выполняется сразу.
    Сеть не дергаем: заглушка import_price_from_url в модуле tasks.
    """
    client: APIClient = APIClient()
    base: str = "/api/v1"
    yaml_path: Path = Path(__file__).resolve().parents[2] / "data" / "shop1.yaml"

    shop_user: User = User.objects.create_user(
        email="celery_shop@example.com",
        password="ShopPass123!!",
        first_name="Ц",
        last_name="Л",
        type=UserType.SHOP,
        is_active=True,
    )
    import_price_from_bytes(yaml_path.read_bytes(), int(shop_user.id))
    shop_row: Shop = Shop.objects.get(user_id=shop_user.id)

    admin_user: User = User.objects.create_user(
        email="admin_import@example.com",
        password="AdminPass123!!",
        first_name="А",
        last_name="Д",
        type=UserType.BUYER,
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )

    login = client.post(
        f"{base}/user/login",
        {"email": admin_user.email, "password": "AdminPass123!!"},
        format="json",
    )
    assert login.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Token {login.json()['Token']}")

    test_url: str = "https://example.com/remote.yaml"
    with patch("catalog.tasks.import_price_from_url", return_value=shop_row) as mocked_import:
        resp = client.post(
            f"{base}/admin/import_task",
            {"url": test_url, "shop_user_id": shop_user.id},
            format="json",
        )

    assert resp.status_code == 200
    body: dict[str, object] = resp.json()
    assert body["Status"] is True
    assert "task_id" in body and isinstance(body["task_id"], str)
    mocked_import.assert_called_once_with(test_url, int(shop_user.id))


@pytest.mark.django_db
def test_partner_endpoints_forbidden_for_buyer() -> None:
    """Партнёрские пути недоступны покупателю (403)."""
    client: APIClient = APIClient()
    base: str = "/api/v1"
    buyer: User = User.objects.create_user(
        email="only_buyer@example.com",
        password="ComplexPass123!",
        first_name="Б",
        last_name="П",
        type=UserType.BUYER,
        is_active=True,
    )
    token: str = client.post(
        f"{base}/user/login",
        {"email": buyer.email, "password": "ComplexPass123!"},
        format="json",
    ).json()["Token"]
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    for path in ("partner/state", "partner/orders", "partner/export"):
        r = client.get(f"{base}/{path}")
        assert r.status_code == 403, path

    r_post = client.post(f"{base}/partner/update", {"url": "https://example.com/x.yaml"}, format="json")
    assert r_post.status_code == 403
