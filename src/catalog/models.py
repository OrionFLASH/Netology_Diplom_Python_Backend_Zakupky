"""
Модели предметной области: пользователи, магазины, категории, товары, заказы, контакты.

Структура согласована с методичкой Netology (этап 2) с расширениями для полей контакта
и текстового описания товара в каталоге.
"""
from __future__ import annotations

import secrets
from typing import Any

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class OrderState(models.TextChoices):
    """Статусы заказа: корзина и этапы исполнения."""

    BASKET = "basket", "Статус корзины"
    NEW = "new", "Новый"
    CONFIRMED = "confirmed", "Подтверждён"
    ASSEMBLED = "assembled", "Собран"
    SENT = "sent", "Отправлен"
    DELIVERED = "delivered", "Доставлен"
    CANCELED = "canceled", "Отменён"


class UserType(models.TextChoices):
    """Тип учётной записи: магазин (партнёр) или покупатель."""

    SHOP = "shop", "Магазин"
    BUYER = "buyer", "Покупатель"


class UserManager(BaseUserManager):
    """Менеджер пользователей с входом по email."""

    use_in_migrations: bool = True

    def _create_user(self, email: str, password: str | None, **extra_fields: Any) -> AbstractUser:
        if not email:
            raise ValueError("Email обязателен")
        email_norm: str = self.normalize_email(email)
        user: User = self.model(email=email_norm, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> AbstractUser:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: Any) -> AbstractUser:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Пользователь сервиса: покупатель или представитель магазина.
    Аутентификация по полю email (USERNAME_FIELD).
    """

    REQUIRED_FIELDS: list[str] = []
    objects: UserManager = UserManager()
    USERNAME_FIELD: str = "email"

    email: models.EmailField = models.EmailField(_("email address"), unique=True)
    company: models.CharField = models.CharField(verbose_name="Компания", max_length=40, blank=True)
    position: models.CharField = models.CharField(verbose_name="Должность", max_length=40, blank=True)
    username_validator = UnicodeUsernameValidator()
    username: models.CharField = models.CharField(
        _("username"),
        max_length=150,
        help_text=_("Обязательное поле. Не более 150 символов."),
        validators=[username_validator],
        error_messages={"unique": _("Пользователь с таким именем уже существует.")},
    )
    is_active: models.BooleanField = models.BooleanField(
        _("active"),
        default=False,
        help_text=_("Неактивные пользователи не могут войти до подтверждения email."),
    )
    type: models.CharField = models.CharField(
        verbose_name="Тип пользователя",
        choices=UserType.choices,
        max_length=5,
        default=UserType.BUYER,
    )

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Username остаётся обязательным полем в AbstractUser; для API регистрации по email
        # подставляем уникальное значение на основе email, если явно не задано.
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    class Meta:
        verbose_name: str = "Пользователь"
        verbose_name_plural: str = "Список пользователей"
        ordering: tuple[str, ...] = ("email",)


class Shop(models.Model):
    """Магазин-партнёр: привязан к пользователю типа shop, может принимать или отключать заказы."""

    name: models.CharField = models.CharField(max_length=50, verbose_name="Название")
    url: models.URLField = models.URLField(verbose_name="Ссылка", null=True, blank=True)
    user: models.OneToOneField[User] = models.OneToOneField(
        User,
        verbose_name="Пользователь",
        blank=True,
        null=True,
        related_name="shop",
        on_delete=models.CASCADE,
    )
    state: models.BooleanField = models.BooleanField(verbose_name="Статус приёма заказов", default=True)

    class Meta:
        verbose_name: str = "Магазин"
        verbose_name_plural: str = "Список магазинов"
        ordering: tuple[str, ...] = ("-name",)

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    """Категория товаров; связь с магазинами many-to-many (товары одной категории в разных магазинах)."""

    name: models.CharField = models.CharField(max_length=40, verbose_name="Название")
    shops: models.ManyToManyField[Shop, Shop] = models.ManyToManyField(
        Shop,
        verbose_name="Магазины",
        related_name="categories",
        blank=True,
    )

    class Meta:
        verbose_name: str = "Категория"
        verbose_name_plural: str = "Список категорий"
        ordering: tuple[str, ...] = ("-name",)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """Номенклатурная позиция (без цены): название, категория и необязательное описание."""

    name: models.CharField = models.CharField(max_length=80, verbose_name="Название")
    category: models.ForeignKey[Category] = models.ForeignKey(
        Category,
        verbose_name="Категория",
        related_name="products",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    description: models.TextField = models.TextField(verbose_name="Описание", blank=True, default="")

    class Meta:
        verbose_name: str = "Продукт"
        verbose_name_plural: str = "Список продуктов"
        ordering: tuple[str, ...] = ("-name",)

    def __str__(self) -> str:
        return self.name


class ProductInfo(models.Model):
    """
    Предложение товара в конкретном магазине: цена, остаток, внешний идентификатор из прайса.
    """

    model: models.CharField = models.CharField(max_length=80, verbose_name="Модель", blank=True)
    external_id: models.PositiveIntegerField = models.PositiveIntegerField(verbose_name="Внешний ИД")
    product: models.ForeignKey[Product] = models.ForeignKey(
        Product,
        verbose_name="Продукт",
        related_name="product_infos",
        on_delete=models.CASCADE,
    )
    shop: models.ForeignKey[Shop] = models.ForeignKey(
        Shop,
        verbose_name="Магазин",
        related_name="product_infos",
        on_delete=models.CASCADE,
    )
    quantity: models.PositiveIntegerField = models.PositiveIntegerField(verbose_name="Количество")
    price: models.PositiveIntegerField = models.PositiveIntegerField(verbose_name="Цена")
    price_rrc: models.PositiveIntegerField = models.PositiveIntegerField(verbose_name="Рекомендуемая розничная цена")

    class Meta:
        verbose_name: str = "Информация о продукте"
        verbose_name_plural: str = "Информационный список о продуктах"
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["product", "shop", "external_id"],
                name="catalog_unique_product_info",
            ),
        ]


class Parameter(models.Model):
    """Имя настраиваемой характеристики товара (например, «Цвет», «Диагональ»)."""

    name: models.CharField = models.CharField(max_length=40, verbose_name="Название", unique=True)

    class Meta:
        verbose_name: str = "Имя параметра"
        verbose_name_plural: str = "Список имён параметров"
        ordering: tuple[str, ...] = ("-name",)

    def __str__(self) -> str:
        return self.name


class ProductParameter(models.Model):
    """Значение параметра для конкретного предложения ProductInfo."""

    product_info: models.ForeignKey[ProductInfo] = models.ForeignKey(
        ProductInfo,
        verbose_name="Информация о продукте",
        related_name="product_parameters",
        on_delete=models.CASCADE,
    )
    parameter: models.ForeignKey[Parameter] = models.ForeignKey(
        Parameter,
        verbose_name="Параметр",
        related_name="product_parameters",
        on_delete=models.CASCADE,
    )
    value: models.CharField = models.CharField(verbose_name="Значение", max_length=100)

    class Meta:
        verbose_name: str = "Параметр"
        verbose_name_plural: str = "Список параметров"
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["product_info", "parameter"],
                name="catalog_unique_product_parameter",
            ),
        ]


class Contact(models.Model):
    """
    Контактные данные покупателя: до пяти адресов доставки на пользователя (проверка в API).
    Дополнительные ФИО и email контактного лица — по сценарию экранов сервиса.
    """

    MAX_ADDRESSES_PER_USER: int = 5

    user: models.ForeignKey[User] = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        related_name="contacts",
        on_delete=models.CASCADE,
    )
    first_name: models.CharField = models.CharField(verbose_name="Имя", max_length=40, blank=True)
    last_name: models.CharField = models.CharField(verbose_name="Фамилия", max_length=40, blank=True)
    patronymic: models.CharField = models.CharField(verbose_name="Отчество", max_length=40, blank=True)
    contact_email: models.EmailField = models.EmailField(verbose_name="Email контакта", blank=True, default="")
    city: models.CharField = models.CharField(max_length=50, verbose_name="Город")
    street: models.CharField = models.CharField(max_length=100, verbose_name="Улица")
    house: models.CharField = models.CharField(max_length=15, verbose_name="Дом", blank=True)
    structure: models.CharField = models.CharField(max_length=15, verbose_name="Корпус", blank=True)
    building: models.CharField = models.CharField(max_length=15, verbose_name="Строение", blank=True)
    apartment: models.CharField = models.CharField(max_length=15, verbose_name="Квартира", blank=True)
    phone: models.CharField = models.CharField(max_length=20, verbose_name="Телефон")

    class Meta:
        verbose_name: str = "Контакты пользователя"
        verbose_name_plural: str = "Список контактов пользователя"

    def __str__(self) -> str:
        return f"{self.city} {self.street} {self.house}".strip()


class Order(models.Model):
    """Заказ пользователя; в статусе basket используется как единственная корзина на пользователя."""

    user: models.ForeignKey[User] = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        related_name="orders",
        on_delete=models.CASCADE,
    )
    dt: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    state: models.CharField = models.CharField(
        verbose_name="Статус",
        choices=OrderState.choices,
        max_length=15,
    )
    contact: models.ForeignKey[Contact] = models.ForeignKey(
        Contact,
        verbose_name="Контакт",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name: str = "Заказ"
        verbose_name_plural: str = "Список заказов"
        ordering: tuple[str, ...] = ("-dt",)

    def __str__(self) -> str:
        return str(self.dt)


class OrderItem(models.Model):
    """Позиция в заказе: ссылка на предложение ProductInfo и количество."""

    order: models.ForeignKey[Order] = models.ForeignKey(
        Order,
        verbose_name="Заказ",
        related_name="ordered_items",
        on_delete=models.CASCADE,
    )
    product_info: models.ForeignKey[ProductInfo] = models.ForeignKey(
        ProductInfo,
        verbose_name="Информация о продукте",
        related_name="ordered_items",
        on_delete=models.CASCADE,
    )
    quantity: models.PositiveIntegerField = models.PositiveIntegerField(verbose_name="Количество")

    class Meta:
        verbose_name: str = "Заказанная позиция"
        verbose_name_plural: str = "Список заказанных позиций"
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["order", "product_info"],
                name="catalog_unique_order_item",
            ),
        ]


class ConfirmEmailToken(models.Model):
    """Одноразовый токен подтверждения регистрации, отправляется на email пользователя."""

    class Meta:
        verbose_name: str = "Токен подтверждения Email"
        verbose_name_plural: str = "Токены подтверждения Email"

    @staticmethod
    def generate_key() -> str:
        """Генерация ключа достаточной длины для безопасной передачи по email."""
        return secrets.token_urlsafe(48)[:64]

    user: models.ForeignKey[User] = models.ForeignKey(
        User,
        related_name="confirm_email_tokens",
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    key: models.CharField = models.CharField(_("Ключ"), max_length=64, db_index=True, unique=True)

    def save(self, *args: Any, **kwargs: Any) -> Any:
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Токен подтверждения для {self.user_id}"
