"""
Представления регистрации, подтверждения email, входа и редактирования профиля.
"""
from __future__ import annotations

import logging

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from catalog.models import ConfirmEmailToken, User, UserType
from catalog.privacy import mask_email
from catalog.serializers import UserSerializer

logger: logging.Logger = logging.getLogger("catalog")


class RegisterAccount(APIView):
    """Регистрация покупателя; пользователь создаётся неактивным до подтверждения email."""

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        required: set[str] = {"first_name", "last_name", "email", "password", "company", "position"}
        if not required.issubset(request.data):
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        try:
            validate_password(request.data["password"])
        except Exception as password_error:  # noqa: BLE001 — Django возвращает список ошибок валидации
            error_array: list[str] = [str(item) for item in password_error]
            return JsonResponse({"Status": False, "Errors": {"password": error_array}})

        serializer: UserSerializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({"Status": False, "Errors": serializer.errors})

        user: User = serializer.save()
        user.set_password(request.data["password"])
        user.type = UserType.BUYER
        user.is_active = False
        user.save()
        logger.info(
            "Зарегистрирован пользователь %s",
            mask_email(user.email),
            extra={"caller_class": "RegisterAccount", "caller_def": "post"},
        )
        return JsonResponse({"Status": True})


class ConfirmAccount(APIView):
    """Активация учётной записи по email и токену из письма."""

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not {"email", "token"}.issubset(request.data):
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        token_obj: ConfirmEmailToken | None = (
            ConfirmEmailToken.objects.filter(user__email=request.data["email"], key=request.data["token"]).first()
        )
        if token_obj is None:
            return JsonResponse({"Status": False, "Errors": "Неправильно указан токен или email"})

        token_obj.user.is_active = True
        token_obj.user.save(update_fields=["is_active"])
        token_obj.delete()
        logger.info(
            "Подтверждён email %s",
            mask_email(request.data["email"]),
            extra={"caller_class": "ConfirmAccount", "caller_def": "post"},
        )
        return JsonResponse({"Status": True})


class AccountDetails(APIView):
    """Просмотр и частичное обновление профиля авторизованного пользователя."""

    def get(self, request: Request, *args: object, **kwargs: object) -> JsonResponse | Response:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)
        serializer: UserSerializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        if "password" in request.data:
            try:
                validate_password(request.data["password"])
            except Exception as password_error:  # noqa: BLE001
                error_array = [str(item) for item in password_error]
                return JsonResponse({"Status": False, "Errors": {"password": error_array}})
            request.user.set_password(request.data["password"])

        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(
                "Обновлён профиль пользователя %s",
                mask_email(request.user.email),
                extra={"caller_class": "AccountDetails", "caller_def": "post"},
            )
            return JsonResponse({"Status": True})
        return JsonResponse({"Status": False, "Errors": serializer.errors})


class LoginAccount(APIView):
    """Выдача токена DRF Token при успешной аутентификации."""

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not {"email", "password"}.issubset(request.data):
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        user = authenticate(request, username=request.data["email"], password=request.data["password"])
        if user is not None and user.is_active:
            token, _ = Token.objects.get_or_create(user=user)
            logger.info(
                "Успешный вход %s",
                mask_email(user.email),
                extra={"caller_class": "LoginAccount", "caller_def": "post"},
            )
            return JsonResponse({"Status": True, "Token": token.key})
        return JsonResponse({"Status": False, "Errors": "Не удалось авторизовать"})
