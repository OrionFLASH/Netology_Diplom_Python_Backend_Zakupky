# Backend сервиса закупок (дипломный проект)

Учебный дипломный проект по курсу Netology: REST API на **Django 5** и **Django REST Framework** для автоматизации заказов товаров в розничной сети. Реализованы каталог с настраиваемыми характеристиками товаров, импорт прайсов в формате YAML, корзина и оформление заказа, уведомления по электронной почте, роли «покупатель» и «магазин», а также продвинутые возможности: экспорт каталога, админка заказов, фоновые задачи **Celery** и пример **docker-compose**.

## Формулировка задачи и техническое задание (кратко)

- Разработать backend для заказа товаров у нескольких поставщиков через единый каталог.  
- Спроектировать модели: магазин, категория, товар, цены по магазинам, параметры, заказ, контакты.  
- Реализовать импорт (и по заданию продвинутой части — экспорт) YAML-прайсов.  
- Реализовать API, совместимый по смыслу с учебным примером (`/api/v1/...`).  
- Отправлять письма: подтверждение регистрации, подтверждение заказа покупателю, накладную администратору, уведомления о смене статуса.  
- Обеспечить логирование с **маскированием персональных данных** в сообщениях.  
- Вынести медленные операции в Celery (отправка писем и импорт по сценарию с очередью).  

Полные формулировки и этапы см. в репозитории курса и в `Docs/README_istochniki.md`.

## Структура репозитория

| Путь | Назначение |
|------|------------|
| `manage.py` | Запуск Django; добавляет `src` в `sys.path`. |
| `zakupki/` | Настройки проекта, корневые URL, WSGI/ASGI, Celery, форматтер логов. |
| `src/catalog/` | Основное приложение: модели, API, сервисы, сигналы, задачи Celery, админка. |
| `src/catalog/api` (логически) | Представления разнесены по файлам `views_*.py`. |
| `src/catalog/services/` | Импорт/экспорт YAML, почтовые уведомления. |
| `src/Tests/` | Автотесты `pytest-django`. |
| `data/` | Пример `shop1.yaml` для импорта. |
| `Docs/` | Ссылки на исходные материалы задания. |
| `log/` | Файлы логов (не коммитятся, см. `.gitignore`). |

## Установка и запуск

### macOS (рекомендуемый порядок)

1. Установите Python 3.12+ (официальный установщик или Homebrew).  
2. В каталоге проекта:  
   `python3 -m venv .venv`  
   `source .venv/bin/activate`  
   `pip install -r requirements.txt`  
3. Скопируйте `cp .env.example .env` и при необходимости задайте `ADMIN_ORDER_EMAIL` для накладных.  
4. `python manage.py migrate`  
5. `python manage.py createsuperuser` (email как логин).  
6. Создайте пользователя-магазина (тип `shop`) в админке или через shell и выполните импорт:  
   `python manage.py import_shop_yaml data/shop1.yaml --email shop@example.com`  
7. `python manage.py runserver` — API: `http://127.0.0.1:8000/api/v1/`.

### Linux

Аналогично macOS; вместо `source .venv/bin/activate` используйте стандартную активацию venv вашего дистрибутива. Для фоновых задач установите Redis (`redis-server`) и задайте `CELERY_BROKER_URL` в `.env`.

### Windows

Рекомендации курса — по возможности использовать macOS/Linux. На Windows те же команды в PowerShell, активация venv: `.venv\Scripts\activate`. Пути к файлам указывайте в стиле ОС. Redis и Celery на Windows настраиваются сложнее; для проверки задания достаточно режима без Celery (`USE_CELERY_FOR_SLOW_OPS=False` по умолчанию).

### Docker Compose

```bash
docker compose up --build
```

Веб: порт `8000`, Redis: `6379`. Перед первым запуском выполните миграции внутри контейнера:  
`docker compose exec web python manage.py migrate`.

### Переменные окружения (`.env`)

| Переменная | Назначение |
|------------|------------|
| `DJANGO_SECRET_KEY` | Секретный ключ Django. |
| `DJANGO_DEBUG` | Режим отладки (`True`/`False`). |
| `DJANGO_ALLOWED_HOSTS` | Список хостов через запятую. |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | Настройки SMTP и отправителя. |
| `ADMIN_ORDER_EMAIL` | Получатель накладной по заказу. |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Подключение Redis для Celery. |
| `USE_CELERY_FOR_SLOW_OPS` | `True` — тяжёлые письма/импорт через Celery. |
| `EMAIL_BACKEND` | По умолчанию в коде — консольный backend для разработки. |

## Основные endpoint’ы API (`/api/v1/`)

| Метод и путь | Назначение |
|--------------|------------|
| `POST /user/register` | Регистрация покупателя (`first_name`, `last_name`, `email`, `password`, `company`, `position`). |
| `POST /user/register/confirm` | Подтверждение email (`email`, `token`). |
| `POST /user/login` | Вход, в ответе `Token` для заголовка `Authorization: Token …`. |
| `GET/POST /user/details` | Профиль пользователя / обновление (в т.ч. пароль). |
| `GET/POST/PUT/DELETE /user/contact` | Адреса доставки (не более 5 на пользователя). |
| `GET /categories`, `GET /shops` | Справочники. |
| `GET /products?shop_id=&category_id=` | Каталог предложений. |
| `GET/POST/PUT/DELETE /basket` | Корзина; `items` — JSON-строка, как в учебном API. |
| `GET/POST /order` | Список заказов / подтверждение (`id` корзины, `contact`). |
| `PUT /order` | Смена статуса заказа (**только `is_staff`**): `id`, `state`. |
| `POST /partner/update` | Загрузка прайса по URL (тип пользователя `shop`). |
| `GET/POST /partner/state` | Статус приёма заказов магазином. |
| `GET /partner/orders` | Заказы, содержащие товары этого магазина. |
| `GET /partner/export` | Экспорт каталога магазина в YAML. |
| `POST /admin/import_task` | Постановка задачи Celery `do_import` (только администратор). |
| `POST /user/password_reset`, `POST /user/password_reset/confirm` | Сброс пароля (пакет `django-rest-passwordreset`). |

Подробнее о сценариях см. раздел «Тестирование».

## Логирование

- Уровни: записи дублируются в консоль и в каталог `log/`.  
- Имена файлов: `INFO_zakupki_ГГГГММДД_ЧЧ.log`, `DEBUG_zakupki_ГГГГММДД_ЧЧ.log`.  
- Строки **DEBUG** следуют шаблону:  
  `дата время - [DEBUG] - сообщение [class: … | def: …]`  
- В пользовательских логах **не пишутся** полные телефоны, email и адреса: используется модуль `catalog.privacy`.

## Описание решения (архитектура)

- **Модели** (`catalog/models.py`): пользователь с типом `buyer`/`shop`, магазин `Shop`, `Category` (M2M с магазинами), `Product`, `ProductInfo` (цена и остаток по магазину), `Parameter` / `ProductParameter`, `Order` / `OrderItem`, `Contact`, токены подтверждения email.  
- **Сервисы**: разбор YAML и запись в БД (`services/yaml_catalog.py`), обратный экспорт (`services/yaml_export.py`), формирование писем (`services/mail_notifications.py`).  
- **Сигналы** (`catalog/signals.py`): письмо при регистрации, сброс пароля, цепочка уведомлений при смене статуса заказа (включая переход корзина → новый).  
- **Celery** (`catalog/tasks.py`): `send_email_task`, `do_import_task`, вспомогательные задачи для писем.  
- **Админка**: редактирование статуса заказа в списке (`list_editable`) с отправкой уведомлений при сохранении.

## Перечень модулей, классов и функций (основное)

Ниже перечислены ключевые элементы для навигации по коду (не дублирует каждую вспомогательную функцию).

| Модуль / объект | Назначение |
|-----------------|------------|
| `manage.py:main()` | Точка входа CLI, настройка `PYTHONPATH` для `src`. |
| `zakupki/settings.py` | Конфигурация Django, DRF, Celery, логирование. |
| `zakupki/logging_utils.StructuredDebugFormatter` | Формат строк DEBUG с `[class: … \| def: …]`. |
| `zakupki/celery.py:app` | Экземпляр Celery. |
| `catalog.models.User`, `UserManager` | Пользователь, вход по email. |
| `catalog.models.Shop`, `Category`, `Product`, `ProductInfo`, `Parameter`, `ProductParameter` | Каталог и характеристики. |
| `catalog.models.Order`, `OrderItem`, `OrderState` | Заказы и статусы. |
| `catalog.models.Contact` | Адреса доставки и контактные поля. |
| `catalog.models.ConfirmEmailToken` | Подтверждение регистрации. |
| `catalog.privacy.*` | Маскирование ПДн для логов. |
| `catalog.services.yaml_catalog.import_price_from_*` | Импорт прайса из байтов/URL. |
| `catalog.services.yaml_export.dump_shop_catalog_yaml` | Экспорт каталога в YAML. |
| `catalog.services.mail_notifications.*` | Тексты и отправка писем. |
| `catalog.signals.*` | Реакции на события моделей и сброс пароля. |
| `catalog.tasks.*` | Фоновые задачи Celery. |
| `catalog.views_*` | Контроллеры API, разбиты по областям. |
| `catalog.management.commands.import_shop_yaml` | Команда загрузки локального YAML. |

Пример команды импорта:

```bash
python manage.py import_shop_yaml data/shop1.yaml --email partner@example.com
```

## Тестирование

```bash
source .venv/bin/activate
pytest src/Tests -q
```

Сценарий `test_buyer_flow` проверяет: регистрацию, подтверждение email, вход, импорт прайса, добавление в корзину, создание контакта, подтверждение заказа и появление писем в `mail.outbox`.

Ручная проверка (кратко):

1. Импортировать прайс для магазина.  
2. Зарегистрировать покупателя, подтвердить токен из письма (в консольном backend — из вывода сервера).  
3. Получить токен входа, заполнить корзину (`POST /basket` с полем `items` — JSON-строка).  
4. Создать контакт, подтвердить заказ `POST /order`.  
5. Убедиться в наличии писем покупателю и (если задан `ADMIN_ORDER_EMAIL`) администратору.

## История версий

| Версия | Изменения |
|--------|-----------|
| 0.1.0 | Каркас проекта, настройки, логирование, подключение DRF и Celery. |
| 0.2.0 | Модели каталога и заказов, миграции, админка. |
| 0.3.0 | Импорт YAML, сериализаторы, API `/api/v1`, корзина и заказы. |
| 0.4.0 | Почтовые уведомления, маскирование ПДн в логах, сигналы статусов. |
| 0.5.0 | Экспорт каталога, задачи Celery, endpoint запуска импорта для администратора, docker-compose, автотесты. |

## Дополнительная документация

- `Docs/README_istochniki.md` — ссылки на репозиторий задания и Postman.  
- Спецификация в репозитории Netology: `reference/api.md`, `reference/screens.md` (ориентиры для проверки сценариев).
