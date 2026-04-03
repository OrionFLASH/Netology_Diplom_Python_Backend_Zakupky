"""
Общие фикстуры pytest-django: in-memory почта для проверки уведомлений.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _email_backend_locmem(settings: object) -> None:
    # Объект settings из pytest-django: подмена backend для доступа к mail.outbox в тестах.
    setattr(settings, "EMAIL_BACKEND", "django.core.mail.backends.locmem.EmailBackend")
