"""
WSGI-конфигурация для развёртывания на совместимых серверах приложений.
"""
from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zakupki.settings")

application = get_wsgi_application()
