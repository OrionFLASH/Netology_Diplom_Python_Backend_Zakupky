"""
Вспомогательные классы для настройки logging (формат DEBUG по учебному шаблону).
"""
from __future__ import annotations

import logging
from typing import Any


class StructuredDebugFormatter(logging.Formatter):
    """
    Форматтер для уровня DEBUG: добавляет в строку контекст вызывающего класса и функции.

    Поля caller_class и caller_def передаются через LoggerAdapter/extra при логировании
    из сервисных модулей; если не заданы — подставляются прочерки.
    """

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "caller_class"):
            record.caller_class = "-"
        if not hasattr(record, "caller_def"):
            record.caller_def = "-"
        return super().format(record)
