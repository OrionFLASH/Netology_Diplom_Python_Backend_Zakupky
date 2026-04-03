# Backend сервиса закупок (дипломный проект)

Учебный **дипломный проект** по курсу Netology: REST API на **Django 5** и **Django REST Framework** для автоматизации заказов товаров в розничной сети. Реализованы каталог с **настраиваемыми характеристиками** товаров, **импорт и экспорт** прайсов в формате YAML, **корзина** и оформление заказа, **уведомления по email** (подтверждение регистрации, подтверждение заказа, накладная администратору, смена статуса), роли **покупатель** и **магазин**, **админ-панель** заказов, фоновые задачи **Celery**, пример **Docker Compose**.

---

## Содержание документации

| Документ | Описание |
|----------|----------|
| **Этот файл (`README.md`)** | Обзор, быстрый старт, оглавление, версии, ссылки на детали |
| [Docs/INDEX.md](Docs/INDEX.md) | Навигация по всем файлам в `Docs/` |
| [Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md) | Слои кода, модели, сигналы, потоки заказа и почты |
| [Docs/API.md](Docs/API.md) | Полное описание REST API с телами запросов и ответами |
| [Docs/DEPLOYMENT.md](Docs/DEPLOYMENT.md) | macOS, Linux, Windows, Docker, Celery, переменные окружения |
| [Docs/IMPORT_EXPORT.md](Docs/IMPORT_EXPORT.md) | Формат YAML, команда импорта, эндпоинты импорта/экспорта |
| [Docs/LOGGING.md](Docs/LOGGING.md) | Файлы логов, формат DEBUG, маскирование ПДн |
| [Docs/TESTING.md](Docs/TESTING.md) | Pytest, ручные сценарии, проверка Celery |
| [Docs/README_istochniki.md](Docs/README_istochniki.md) | Ссылки на репозиторий задания и Postman |

---

## Краткая формулировка задания

- Backend для заказа товаров у **нескольких поставщиков** через единый каталог.  
- Модели: магазин, категория, товар, цены и остатки по магазинам, параметры, заказ, контакты.  
- API в духе учебного примера: префикс **`/api/v1/`**.  
- Письма: регистрация, клиент при заказе, **накладная** на `ADMIN_ORDER_EMAIL`, уведомления при смене статуса.  
- Логи с **маскированием** чувствительных данных.  
- Продвинутая часть: экспорт YAML, админка, Celery, docker-compose.

Первоисточник формулировок: репозиторий курса (см. `Docs/README_istochniki.md`).

---

## Структура репозитория

| Путь | Назначение |
|------|------------|
| `manage.py` | CLI Django; добавляет `src` в `sys.path`. |
| `zakupki/` | Настройки, корневые URL, WSGI/ASGI, Celery, форматтер DEBUG-логов. |
| `src/catalog/` | Приложение: `models.py`, `serializers.py`, `views_*.py`, `signals.py`, `tasks.py`, `admin.py`, `services/`, `management/commands/`. |
| `src/Tests/` | Автотесты (`pytest-django`). |
| `data/` | Пример **`shop1.yaml`**. |
| `Docs/` | Подробная документация (см. таблицу выше). |
| `log/` | Ротация логов (файлы `*.log` не коммитятся). |
| `Dockerfile`, `docker-compose.yml` | Контейнеры `web`, `celery`, `redis`. |

Имена модулей отражают зону ответственности: **`views_auth`**, **`views_catalog`**, **`views_basket`**, **`views_contact`**, **`views_order`**, **`views_partner`**.

---

## Быстрый старт (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # заполните SECRET_KEY, при необходимости ADMIN_ORDER_EMAIL
python manage.py migrate
python manage.py createsuperuser
# Создайте в админке пользователя type=shop, затем:
python manage.py import_shop_yaml data/shop1.yaml --email <email_магазина>
python manage.py runserver
```

API: **http://127.0.0.1:8000/api/v1/**  
Админка: **http://127.0.0.1:8000/admin/**

Подробные шаги для разных ОС, Docker и Celery — **[Docs/DEPLOYMENT.md](Docs/DEPLOYMENT.md)**.

---

## Краткая таблица API

Полное описание — **[Docs/API.md](Docs/API.md)**.

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | `/api/v1/user/register` | Регистрация покупателя |
| POST | `/api/v1/user/register/confirm` | Подтверждение email |
| POST | `/api/v1/user/login` | Токен авторизации |
| GET/POST | `/api/v1/user/details` | Профиль |
| GET/POST/PUT/DELETE | `/api/v1/user/contact` | Адреса (макс. 5) |
| GET | `/api/v1/categories`, `/api/v1/shops` | Справочники |
| GET | `/api/v1/products` | Каталог (`shop_id`, `category_id`) |
| GET/POST/PUT/DELETE | `/api/v1/basket` | Корзина (`items` — JSON-строка) |
| GET/POST | `/api/v1/order` | Список/подтверждение заказа |
| PUT | `/api/v1/order` | Статус заказа (только staff) |
| POST | `/api/v1/partner/update` | Импорт прайса по URL (shop) |
| GET/POST | `/api/v1/partner/state` | Приём заказов магазином |
| GET | `/api/v1/partner/orders` | Заказы с товарами магазина |
| GET | `/api/v1/partner/export` | Экспорт YAML |
| POST | `/api/v1/admin/import_task` | Celery-импорт (staff) |
| POST | `/api/v1/user/password_reset` (+ `/confirm`) | Сброс пароля |

---

## Переменные окружения (обзор)

Детально — **[Docs/DEPLOYMENT.md](Docs/DEPLOYMENT.md)**. Шаблон без секретов: **`.env.example`**.

| Переменная | Назначение |
|------------|------------|
| `DJANGO_SECRET_KEY` | Секрет Django |
| `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Режим и хосты |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `EMAIL_BACKEND` | Почта |
| `ADMIN_ORDER_EMAIL` | Получатель накладных |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis для Celery |
| `USE_CELERY_FOR_SLOW_OPS` | Фоновые письма/цепочки |

---

## Логирование и безопасность логов

Кратко: файлы в **`log/`**, шаблон имён с датой и часом, для DEBUG — суффикс **`[class: … | def: …]`**. Персональные данные маскируются (**`catalog.privacy`**). Подробно — **[Docs/LOGGING.md](Docs/LOGGING.md)**.

---

## Тестирование

```bash
pytest src/Tests -v
```

Описание сценария и ручного чек-листа — **[Docs/TESTING.md](Docs/TESTING.md)**.

---

## Справочник по ключевым модулям кода

| Компонент | Файл / пакет |
|-----------|----------------|
| Модели, статусы заказа | `src/catalog/models.py` |
| Сериализаторы | `src/catalog/serializers.py` |
| URL приложения | `src/catalog/urls.py` |
| Импорт/экспорт YAML | `src/catalog/services/yaml_catalog.py`, `yaml_export.py` |
| Письма | `src/catalog/services/mail_notifications.py` |
| Сигналы | `src/catalog/signals.py` |
| Celery | `src/catalog/tasks.py`, `zakupki/celery.py` |
| Маскирование в логах | `src/catalog/privacy.py` |
| Импорт из файла | `python manage.py import_shop_yaml …` |
| Настройки | `zakupki/settings.py` |

---

## История версий

| Версия | Изменения |
|--------|-----------|
| 0.1.0 | Каркас проекта, настройки, логирование, DRF, Celery |
| 0.2.0 | Модели, миграции, админка |
| 0.3.0 | Импорт YAML, API, корзина, заказы |
| 0.4.0 | Почта, сигналы, маскирование ПДн в логах |
| 0.5.0 | Экспорт, Celery-задачи, Docker, pytest |
| 0.5.1 | Исправление `PYTHONPATH` в Docker для воркера Celery |
| **0.6.0** | Расширенная документация в `Docs/`, обновление README |
| **0.6.1** | Корзина: поддержка `items` как JSON-массива; доп. автотест; уточнение `Docs/API.md` |
