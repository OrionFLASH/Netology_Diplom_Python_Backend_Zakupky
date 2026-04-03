"""
Отправка писем: подтверждение регистрации, сброс пароля, уведомления по заказам.

Тексты писем формируются без включения полных ПДн в тему письма; детали заказа — в теле для администратора.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail

from catalog.models import Order, OrderState, User
from catalog.privacy import mask_email

logger: logging.Logger = logging.getLogger("catalog")


def _recipients_ok(addresses: Iterable[str]) -> list[str]:
    """Убирает пустые адреса из списка получателей."""
    return [a.strip() for a in addresses if a and a.strip()]


def send_registration_token_email(user: User, token_key: str) -> None:
    """Письмо с ключом подтверждения регистрации (пользователь ещё не активен)."""
    subject: str = "Подтверждение регистрации в сервисе закупок"
    body: str = (
        f"Здравствуйте, {user.first_name}.\n\n"
        f"Для подтверждения email отправьте token и email в POST /api/v1/user/register/confirm:\n"
        f"token: {token_key}\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    logger.info(
        "Отправлено письмо подтверждения регистрации на %s",
        mask_email(user.email),
        extra={"caller_class": "mail_notifications", "caller_def": "send_registration_token_email"},
    )


def build_order_summary_text(order: Order) -> str:
    """Текстовая накладная по заказу для администратора (без маскирования внутри письма — получатель доверенный)."""
    lines: list[str] = [
        f"Заказ #{order.id}",
        f"Дата: {order.dt.isoformat()}",
        f"Статус: {order.state}",
        "",
        "Позиции:",
    ]
    for item in order.ordered_items.select_related("product_info__product", "product_info__shop").all():
        price: int = int(item.product_info.price)
        qty: int = int(item.quantity)
        lines.append(
            f"- {item.product_info.product.name} | магазин: {item.product_info.shop.name} | "
            f"{qty} x {price} = {qty * price}"
        )
    if order.contact_id:
        c = order.contact
        lines.extend(
            [
                "",
                "Доставка:",
                f"{c.city}, {c.street}, д.{c.house} к.{c.structure} стр.{c.building} кв.{c.apartment}",
                f"Телефон: {c.phone}",
            ]
        )
    return "\n".join(lines)


def send_new_order_emails(order: Order) -> None:
    """
    После подтверждения заказа покупателем:
    - клиенту — краткое подтверждение;
    - администратору — накладная для исполнения.
    """
    user: User = order.user
    client_subject: str = f"Заказ #{order.id} принят"
    client_body: str = (
        f"{user.first_name}, ваш заказ #{order.id} принят в обработку.\n"
        f"Текущий статус: {order.get_state_display()}.\n"
    )
    send_mail(
        client_subject,
        client_body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    logger.info(
        "Отправлено подтверждение заказа клиенту %s, заказ #%s",
        mask_email(user.email),
        order.id,
        extra={"caller_class": "mail_notifications", "caller_def": "send_new_order_emails"},
    )

    admin_email: str = getattr(settings, "ADMIN_ORDER_EMAIL", "") or ""
    recipients: list[str] = _recipients_ok([admin_email])
    if not recipients:
        logger.warning(
            "ADMIN_ORDER_EMAIL не задан — накладная администратору не отправлена (заказ #%s)",
            order.id,
            extra={"caller_class": "mail_notifications", "caller_def": "send_new_order_emails"},
        )
        return

    admin_body: str = build_order_summary_text(order)
    msg = EmailMultiAlternatives(
        subject=f"Накладная по заказу #{order.id}",
        body=admin_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    msg.send(fail_silently=False)
    logger.info(
        "Накладная по заказу #%s отправлена администратору",
        order.id,
        extra={"caller_class": "mail_notifications", "caller_def": "send_new_order_emails"},
    )


def send_order_status_changed_email(order: Order, previous_state: str) -> None:
    """Уведомление клиенту при смене статуса заказа (например, из админ-панели)."""
    user: User = order.user
    labels: dict[str, str] = dict(OrderState.choices)
    previous_label: str = labels.get(previous_state, previous_state)
    current_label: str = order.get_state_display()
    subject: str = f"Статус заказа #{order.id} изменён"
    body: str = (
        f"Статус вашего заказа #{order.id} изменён с «{previous_label}» на «{current_label}».\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    logger.info(
        "Уведомление о смене статуса заказа #%s отправлено на %s",
        order.id,
        mask_email(user.email),
        extra={"caller_class": "mail_notifications", "caller_def": "send_order_status_changed_email"},
    )
