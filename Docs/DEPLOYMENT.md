# Развёртывание и окружение

Порядок разделов: **macOS → Linux → Windows**, как рекомендовано для описания учебных проектов.

---

## 1. macOS

### 1.1. Требования

- Python **3.12+** (рекомендуется с python.org или Homebrew).
- Git.
- Для Celery: **Redis** (`brew install redis`, затем `brew services start redis`).

### 1.2. Виртуальное окружение

```bash
cd /путь/к/проекту
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1.3. Переменные окружения

```bash
cp .env.example .env
```

Отредактируйте `.env` (файл в `.gitignore`):

| Переменная | Зачем нужна |
|------------|-------------|
| `DJANGO_SECRET_KEY` | Обязательно уникальное значение вне репозитория. |
| `DJANGO_DEBUG` | `True` только для разработки. |
| `DJANGO_ALLOWED_HOSTS` | Список хостов через запятую для продакшена. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | Реальная отправка писем (Яндекс, Mail.ru и т.д.). |
| `DEFAULT_FROM_EMAIL` | Адрес отправителя в письмах. |
| `ADMIN_ORDER_EMAIL` | Куда слать **накладную** по подтверждённому заказу. |
| `EMAIL_BACKEND` | Для отладки без SMTP: `django.core.mail.backends.console.EmailBackend`. |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | URL Redis, например `redis://127.0.0.1:6379/0`. |
| `USE_CELERY_FOR_SLOW_OPS` | `True` — часть писем и цепочек уходит в Celery (нужен запущенный worker). |

### 1.4. База данных и суперпользователь

```bash
python manage.py migrate
python manage.py createsuperuser
```

Логин в админке — **email**.

### 1.5. Данные для демонстрации

1. В админке создать пользователя с типом **`shop`**, активного, задать пароль.  
2. Импорт прайса:

```bash
python manage.py import_shop_yaml data/shop1.yaml --email <email_магазина>
```

### 1.6. Запуск веб-сервера

```bash
python manage.py runserver
```

API: `http://127.0.0.1:8000/api/v1/`.

### 1.7. Запуск Celery (опционально)

В отдельных терминалах при активированном `.venv` и запущенном Redis:

```bash
celery -A zakupki worker -l info
```

---

## 2. Linux

Шаги совпадают с macOS: `python3 -m venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`.

Установка Redis зависит от дистрибутива, например:

- Debian/Ubuntu: `sudo apt install redis-server` и `sudo systemctl enable --now redis-server`.

Проверка: `redis-cli ping` → `PONG`.

Путь к проекту и права на каталоги `log/` и файл `db.sqlite3` должны позволять пользователю, от имени которого запускается Gunicorn/uwsgi, писать файлы.

---

## 3. Windows

Курс Netology рекомендует macOS/Linux. На Windows возможны:

- Python с python.org, venv: `.venv\Scripts\activate`.
- Пути в командах импорта — в формате Windows: `python manage.py import_shop_yaml C:\data\shop1.yaml --email ...`.

**Redis и Celery** на Windows настраиваются менее удобно (WSL2 часто предпочтительнее нативного Redis). Для зачёта по базовой части достаточно **`USE_CELERY_FOR_SLOW_OPS=False`** (значение по умолчанию): письма и импорт выполняются синхронно в процессе запроса.

---

## 4. Docker Compose

### 4.1. Сборка и запуск

```bash
docker compose up --build -d
```

Сервисы:

- **redis** — порт **6379** на хосте;
- **web** — Django `runserver`, порт **8000**;
- **celery** — воркер очереди.

### 4.2. Миграции

После первого подъёма:

```bash
docker compose exec web python manage.py migrate
```

База **`db.sqlite3`** лежит в смонтированном томе `./` (корень проекта на хосте).

### 4.3. PYTHONPATH в образе

В **Dockerfile** задано **`ENV PYTHONPATH=/app/src:/app`**: процесс **`celery`** не вызывает `manage.py`, поэтому без этого переменная не находила бы пакет `catalog`.

### 4.4. Переменные в compose

В `docker-compose.yml` заданы минимальные значения для разработки (`DJANGO_SECRET_KEY`, брокер Redis, консольный email). Для реальных писем смонтируйте `.env` или расширьте секцию `environment` (не коммитьте секреты в открытом виде).

### 4.5. Логи контейнеров

```bash
docker compose logs -f web
docker compose logs -f celery
```

---

## 5. Зависимости из requirements.txt (назначение)

| Пакет | Роль |
|-------|------|
| Django | Веб-фреймворк и ORM. |
| djangorestframework | REST API, сериализаторы, аутентификация по токену. |
| celery | Фоновые задачи. |
| redis | Брокер сообщений для Celery. |
| requests | Загрузка YAML по URL при импорте прайса. |
| pyyaml | Разбор и сборка YAML. |
| ujson | Быстрый разбор JSON для поля `items` в корзине. |
| django-rest-passwordreset | Сброс пароля по API. |
| python-dotenv | Загрузка `.env` в `settings`. |
| pytest, pytest-django | Автотесты. |
