"""
Маскирование персональных и чувствительных данных для безопасного логирования.

Используется перед записью в лог сообщений, которые могут содержать телефоны, email, адреса.
"""
from __future__ import annotations

import re
from typing import Any


def mask_email(value: str | None) -> str:
    """Маскирует локальную часть email, оставляя домен для диагностики."""
    if not value or "@" not in value:
        return "***"
    local, _, domain = value.partition("@")
    if len(local) <= 1:
        masked_local: str = "*"
    else:
        masked_local = f"{local[0]}***"
    return f"{masked_local}@{domain}"


def mask_phone(value: str | None) -> str:
    """Оставляет только последние 2 цифры номера."""
    if not value:
        return "***"
    digits: str = re.sub(r"\D", "", value)
    if len(digits) <= 2:
        return "**"
    return f"***{digits[-2:]}"


def mask_address_fragment(value: str | None, visible: int = 2) -> str:
    """Сокращает длину фрагмента адреса, оставляя начало для ориентира без полного текста."""
    if not value:
        return "***"
    text: str = value.strip()
    if len(text) <= visible:
        return "***"
    return f"{text[:visible]}***"


def mask_user_id(user_id: int | None) -> str:
    """Не логируем идентификатор пользователя в открытом виде."""
    if user_id is None:
        return "-"
    return f"user_id_hash_{user_id % 10000:04d}"


def safe_contact_log_payload(data: dict[str, Any]) -> dict[str, Any]:
    """
    Возвращает копию словаря контактных данных с заменой чувствительных полей на маски.
    Удобно для логирования входящих тел запросов без утечки ПДн.
    """
    out: dict[str, Any] = {}
    for key, val in data.items():
        lk: str = str(key).lower()
        if lk in {"email", "contact_email"}:
            out[key] = mask_email(str(val)) if val else ""
        elif lk in {"phone", "tel", "telephone"}:
            out[key] = mask_phone(str(val)) if val else ""
        elif lk in {"street", "city", "house", "building", "structure", "apartment", "address"}:
            out[key] = mask_address_fragment(str(val)) if val else ""
        elif lk in {"user", "user_id"}:
            out[key] = mask_user_id(int(val)) if str(val).isdigit() else "***"
        else:
            out[key] = val
    return out
