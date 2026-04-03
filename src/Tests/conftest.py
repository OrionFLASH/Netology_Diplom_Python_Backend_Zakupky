"""
Общие фикстуры pytest-django: in-memory почта для проверки уведомлений.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _email_backend_locmem(settings: object) -> None:
    # Объект settings из pytest-django: подмена backend для доступа к mail.outbox в тестах.
    setattr(settings, "EMAIL_BACKEND", "django.core.mail.backends.locmem.EmailBackend")


@pytest.fixture(autouse=True)
def _celery_tasks_run_eagerly(settings: object) -> None:
    # Celery выполняет .delay() синхронно в процессе теста — без Redis и без отдельного воркера.
    setattr(settings, "CELERY_TASK_ALWAYS_EAGER", True)
