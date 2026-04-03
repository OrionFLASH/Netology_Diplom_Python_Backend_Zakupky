#!/usr/bin/env python
"""
Точка входа Django: загрузка настроек и запуск команд manage.py.
Каталог src добавляется в sys.path, чтобы приложение catalog импортировалось как пакет верхнего уровня.
"""
import os
import sys
from pathlib import Path


def main() -> None:
    """Запуск утилиты командной строки Django."""
    root: Path = Path(__file__).resolve().parent
    src: Path = root / "src"
    src_str: str = str(src)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zakupki.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Убедитесь, что виртуальное окружение активировано "
            "и зависимости установлены (pip install -r requirements.txt)."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
