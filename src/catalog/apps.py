"""
Конфигурация приложения catalog: подключение сигналов при готовности приложения.
"""
from __future__ import annotations

from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """Метаданные приложения и хук ready() для импорта сигналов."""

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "catalog"
    verbose_name: str = "Каталог и заказы"

    def ready(self) -> None:
        # Импорт регистрирует обработчики post_save и кастомные сигналы
        import catalog.signals  # noqa: F401
