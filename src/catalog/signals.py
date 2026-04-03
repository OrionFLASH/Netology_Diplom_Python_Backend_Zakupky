"""
Сигналы Django: подтверждение регистрации, сброс пароля, смена статуса заказа.

Важно: подтверждение заказа выполняется через сохранение модели Order (save), а не через QuerySet.update,
иначе сигналы post_save не вызываются.
"""
from __future__ import annotations

import logging
from typing import Type

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created

from catalog.models import ConfirmEmailToken, Order, OrderState, User
from catalog.privacy import mask_email
from catalog.services.mail_notifications import (
    send_new_order_emails,
    send_order_status_changed_email,
    send_registration_token_email,
)

logger: logging.Logger = logging.getLogger("catalog")


@receiver(reset_password_token_created)
def password_reset_token_created_handler(
    sender: Type,
    instance: object,
    reset_password_token: object,
    **kwargs: object,
) -> None:
    """
    Отправка письма с токеном сброса пароля (django-rest-passwordreset).
    Тема и тело не содержат полного email в заголовке для снижения утечек в логах почтовика.
    """
    user: User = reset_password_token.user  # type: ignore[attr-defined]
    key: str = reset_password_token.key  # type: ignore[attr-defined]
    subject: str = "Восстановление пароля"
    body: str = (
        f"Здравствуйте, {user.first_name}.\n\n"
        f"Токен для сброса пароля: {key}\n"
        "Используйте endpoint /api/v1/user/password_reset/confirm согласно документации API.\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    logger.info(
        "Отправлено письмо сброса пароля на %s",
        mask_email(user.email),
        extra={"caller_class": "signals", "caller_def": "password_reset_token_created_handler"},
    )


@receiver(post_save, sender=User)
def user_post_save_handler(sender: Type[User], instance: User, created: bool, **kwargs: object) -> None:
    """Создание токена и отправка письма при регистрации неактивного пользователя."""
    if not created or instance.is_active:
        return
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)
    send_registration_token_email(instance, token.key)


@receiver(pre_save, sender=Order)
def order_pre_save_handler(sender: Type[Order], instance: Order, **kwargs: object) -> None:
    """Сохраняем предыдущий статус заказа для сравнения в post_save."""
    if not instance.pk:
        instance._previous_state = None  # type: ignore[attr-defined]
        return
    previous: Order | None = Order.objects.filter(pk=instance.pk).only("state").first()
    instance._previous_state = previous.state if previous else None  # type: ignore[attr-defined]


def _dispatch_new_order_emails(order_id: int) -> None:
    """Синхронно или через Celery отправляет письма по новому заказу."""
    if getattr(settings, "USE_CELERY_FOR_SLOW_OPS", False):
        from catalog.tasks import send_order_notifications_task

        send_order_notifications_task.delay(order_id)
        return
    order: Order = (
        Order.objects.filter(pk=order_id)
        .prefetch_related(
            "ordered_items__product_info__product",
            "ordered_items__product_info__shop",
        )
        .first()
    )
    if order is not None:
        send_new_order_emails(order)


def _dispatch_status_email(order_id: int, previous_state: str) -> None:
    if getattr(settings, "USE_CELERY_FOR_SLOW_OPS", False):
        from catalog.tasks import send_order_status_changed_task

        send_order_status_changed_task.delay(order_id, previous_state)
        return
    order: Order | None = Order.objects.filter(pk=order_id).first()
    if order is not None:
        send_order_status_changed_email(order, previous_state)


@receiver(post_save, sender=Order)
def order_post_save_handler(sender: Type[Order], instance: Order, created: bool, **kwargs: object) -> None:
    """
    Уведомления при смене статуса:
    - из корзины в «новый» — подтверждение клиенту и накладная администратору;
    - иные переходы — письмо клиенту об изменении статуса.
    """
    if created:
        return
    previous: str | None = getattr(instance, "_previous_state", None)
    if previous is None or previous == instance.state:
        return

    if previous == OrderState.BASKET and instance.state == OrderState.NEW:
        _dispatch_new_order_emails(instance.id)
        return

    if instance.state != OrderState.BASKET:
        _dispatch_status_email(instance.id, previous)
