from django.urls import path

from . import admin_views as views

urlpatterns = [
    path("fees/", views.fee_list, name="admin_fees"),
    path("fees/add/", views.fee_add, name="admin_fee_add"),
    path("", views.payment_list, name="admin_payments"),
    path("add/", views.payment_add, name="admin_payment_add"),
    path("<int:pk>/<str:action>/", views.payment_action, name="admin_payment_action"),
]
