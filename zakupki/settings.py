"""
Глобальные настройки Django-проекта zakupki.
Секреты и среда читаются из .env (python-dotenv), без хранения паролей в репозитории.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Корень репозитория (родитель каталога zakupki)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    """Безопасное чтение логического флага из переменных окружения."""
    raw: str | None = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY: str = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me-in-production")
DEBUG: bool = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS: list[str] = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]

INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "django_rest_passwordreset",
    "catalog.apps.CatalogConfig",
]

MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF: str = "zakupki.urls"

TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION: str = "zakupki.wsgi.application"

DATABASES: dict[str, dict[str, Any]] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE: str = "ru-ru"
TIME_ZONE: str = "Europe/Moscow"
USE_I18N: bool = True
USE_TZ: bool = True

STATIC_URL: str = "static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"
AUTH_USER_MODEL: str = "catalog.User"

# Почтовый backend: в разработке удобно выводить письма в консоль
EMAIL_BACKEND: str = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST: str = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT: int = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER: str = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD: str = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS: bool = _env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL: bool = _env_bool("EMAIL_USE_SSL", False)
DEFAULT_FROM_EMAIL: str = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@localhost")

# Адрес для накладных и служебных писем по заказам
ADMIN_ORDER_EMAIL: str = os.environ.get("ADMIN_ORDER_EMAIL", "")

REST_FRAMEWORK: dict[str, Any] = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 40,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
}

# Celery
CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER: bool = _env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES: bool = True

# Флаг: отправлять тяжёлые письма и импорт через Celery (если False — синхронно в запросе)
USE_CELERY_FOR_SLOW_OPS: bool = _env_bool("USE_CELERY_FOR_SLOW_OPS", False)

LOG_DIR: Path = BASE_DIR / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _log_filename(prefix: str) -> str:
    """Шаблон имени файла лога: Уровень_тема_годмесяцдень_час (без секунд для ротации по часу)."""
    from datetime import datetime

    now: datetime = datetime.now()
    return str(LOG_DIR / f"{prefix}_zakupki_{now:%Y%m%d_%H}.log")


LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s - [%(levelname)s] - %(message)s",
        },
        "debug_structured": {
            "()": "zakupki.logging_utils.StructuredDebugFormatter",
            "format": "%(asctime)s - [DEBUG] - %(message)s [class: %(caller_class)s | def: %(caller_def)s]",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "info_file": {
            "class": "logging.FileHandler",
            "filename": _log_filename("INFO"),
            "encoding": "utf-8",
            "formatter": "verbose",
        },
        "debug_file": {
            "class": "logging.FileHandler",
            "filename": _log_filename("DEBUG"),
            "encoding": "utf-8",
            "formatter": "debug_structured",
        },
    },
    "loggers": {
        "catalog": {
            "handlers": ["console", "info_file", "debug_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "info_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
