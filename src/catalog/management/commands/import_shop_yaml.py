"""
Команда управления: импорт локального YAML-файла прайса от имени пользователя-магазина.

Пример:
  python manage.py import_shop_yaml data/shop1.yaml --email shop@example.com
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from catalog.models import User, UserType
from catalog.services.yaml_catalog import import_price_from_bytes

logger: logging.Logger = logging.getLogger("catalog")


class Command(BaseCommand):
    """Загрузка файла с диска в модели каталога (без HTTP)."""

    help: str = "Импорт YAML-прайса из файла для указанного пользователя типа «магазин»."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("path", type=str, help="Путь к YAML-файлу")
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email пользователя-магазина (должен существовать и иметь type=shop)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        file_path: Path = Path(options["path"]).resolve()
        if not file_path.is_file():
            raise CommandError(f"Файл не найден: {file_path}")

        email: str = options["email"]
        user: User | None = User.objects.filter(email=email).first()
        if user is None:
            raise CommandError(f"Пользователь с email {email} не найден")
        if user.type != UserType.SHOP:
            raise CommandError("Пользователь должен иметь тип shop")

        raw: bytes = file_path.read_bytes()
        shop = import_price_from_bytes(raw, int(user.id))
        logger.info(
            "Импорт из файла %s выполнен для магазина %s",
            file_path.name,
            shop.name,
            extra={"caller_class": "import_shop_yaml", "caller_def": "handle"},
        )
        self.stdout.write(self.style.SUCCESS(f"Импортирован магазин «{shop.name}» ({file_path})"))
