"""
Пакет настроек Django-проекта zakupki.
При импорте инициализируется Celery-приложение (для воркеров и веб-процесса).
"""

from __future__ import annotations

from zakupki.celery import app as celery_app

__all__: tuple[str, ...] = ("celery_app",)
