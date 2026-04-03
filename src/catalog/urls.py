"""
Маршруты приложения catalog под префиксом /api/v1/.
"""
from __future__ import annotations

from django.urls import path

from catalog.views_auth import AccountDetails, ConfirmAccount, LoginAccount, RegisterAccount
from catalog.views_basket import BasketView
from catalog.views_catalog import CategoryView, ProductInfoView, ShopView
from catalog.views_contact import ContactView
from catalog.views_order import OrderView
from catalog.views_partner import (
    AdminImportTaskView,
    PartnerExportView,
    PartnerOrders,
    PartnerState,
    PartnerUpdate,
)

app_name: str = "catalog"

urlpatterns: list[path] = [
    path("partner/update", PartnerUpdate.as_view(), name="partner-update"),
    path("partner/state", PartnerState.as_view(), name="partner-state"),
    path("partner/orders", PartnerOrders.as_view(), name="partner-orders"),
    path("partner/export", PartnerExportView.as_view(), name="partner-export"),
    path("admin/import_task", AdminImportTaskView.as_view(), name="admin-import-task"),
    path("user/register", RegisterAccount.as_view(), name="user-register"),
    path("user/register/confirm", ConfirmAccount.as_view(), name="user-register-confirm"),
    path("user/details", AccountDetails.as_view(), name="user-details"),
    path("user/contact", ContactView.as_view(), name="user-contact"),
    path("user/login", LoginAccount.as_view(), name="user-login"),
    path("categories", CategoryView.as_view(), name="categories"),
    path("shops", ShopView.as_view(), name="shops"),
    path("products", ProductInfoView.as_view(), name="products"),
    path("basket", BasketView.as_view(), name="basket"),
    path("order", OrderView.as_view(), name="order"),
]
