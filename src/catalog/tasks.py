"""
Задачи Celery: рассылка писем и фоновый импорт прайса (медленные операции вне HTTP-запроса).
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.core.mail import send_mail

from catalog.models import Order
from catalog.services.mail_notifications import send_new_order_emails, send_order_status_changed_email
from catalog.services.yaml_catalog import import_price_from_url

logger: logging.Logger = logging.getLogger("catalog")


@shared_task
def send_email_task(subject: str, body: str, recipient: str, from_email: str) -> None:
    """
    Универсальная отправка письма (требование задания: отдельная задача send_email).

    Используется точечно, когда нужно вынести отправку в очередь явно.
    """
    send_mail(subject, body, from_email, [recipient], fail_silently=False)
    logger.info(
        "Celery send_email_task: письмо отправлено",
        extra={"caller_class": "tasks", "caller_def": "send_email_task"},
    )


@shared_task
def do_import_task(url: str, shop_user_id: int) -> str:
    """
    Фоновый импорт YAML по URL для пользователя-магазина.

    Возвращает строку с именем магазина для отображения в ответе API.
    """
    shop = import_price_from_url(url, shop_user_id)
    logger.info(
        "Celery do_import_task завершён для магазина %s",
        shop.name,
        extra={"caller_class": "tasks", "caller_def": "do_import_task"},
    )
    return shop.name


@shared_task
def send_order_notifications_task(order_id: int) -> None:
    """Отложенная отправка подтверждения заказа и накладной."""
    order: Order | None = (
        Order.objects.filter(pk=order_id)
        .prefetch_related(
            "ordered_items__product_info__product",
            "ordered_items__product_info__shop",
        )
        .first()
    )
    if order is None:
        return
    send_new_order_emails(order)


@shared_task
def send_order_status_changed_task(order_id: int, previous_state: str) -> None:
    """Отложенное уведомление клиента о смене статуса заказа."""
    order: Order | None = Order.objects.filter(pk=order_id).first()
    if order is None:
        return
    send_order_status_changed_email(order, previous_state)
