"""
Адреса доставки пользователя (контакты).
"""
from __future__ import annotations

import logging

from django.db.models import Q
from django.http import JsonResponse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Contact
from catalog.privacy import mask_user_id, safe_contact_log_payload
from catalog.serializers import ContactSerializer

logger: logging.Logger = logging.getLogger("catalog")


class ContactView(APIView):
    """CRUD контактов с ограничением не более пяти адресов на пользователя."""

    def get(self, request: Request, *args: object, **kwargs: object) -> JsonResponse | Response:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)
        contacts = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    def post(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        if not {"city", "street", "phone"}.issubset(request.data):
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        if Contact.objects.filter(user_id=request.user.id).count() >= Contact.MAX_ADDRESSES_PER_USER:
            return JsonResponse(
                {"Status": False, "Errors": f"Превышен лимит адресов ({Contact.MAX_ADDRESSES_PER_USER})"},
            )

        data = request.data.copy()
        data["user"] = request.user.id
        serializer = ContactSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            logger.info(
                "Добавлен контакт пользователя %s: %s",
                mask_user_id(request.user.id),
                safe_contact_log_payload(dict(data)),
                extra={"caller_class": "ContactView", "caller_def": "post"},
            )
            return JsonResponse({"Status": True})
        return JsonResponse({"Status": False, "Errors": serializer.errors})

    def delete(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        items_string: str | None = request.data.get("items")
        if not items_string:
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        items_list: list[str] = items_string.split(",")
        query: Q = Q()
        objects_deleted: bool = False
        for contact_id in items_list:
            if contact_id.strip().isdigit():
                query |= Q(user_id=request.user.id, id=int(contact_id))
                objects_deleted = True

        if objects_deleted:
            deleted_count: int = Contact.objects.filter(query).delete()[0]
            return JsonResponse({"Status": True, "Удалено объектов": deleted_count})
        return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

    def put(self, request: Request, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": "Log in required"}, status=403)

        contact_id = request.data.get("id")
        if contact_id is None:
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        cid: str = str(contact_id)
        if not cid.isdigit():
            return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})

        contact: Contact | None = Contact.objects.filter(id=int(cid), user_id=request.user.id).first()
        if contact is None:
            return JsonResponse({"Status": False, "Errors": "Контакт не найден"})

        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(
                "Обновлён контакт %s пользователя %s",
                cid,
                mask_user_id(request.user.id),
                extra={"caller_class": "ContactView", "caller_def": "put"},
            )
            return JsonResponse({"Status": True})
        return JsonResponse({"Status": False, "Errors": serializer.errors})
