from django.urls import path

from . import views

urlpatterns = [
    path("", views.fee_summary, name="fee_summary"),
    path("history/", views.payment_history, name="payment_history"),
    path("<int:pk>/", views.payment_detail, name="payment_detail"),
    path("<int:pk>/receipt/", views.receipt, name="payment_receipt"),
    path("fee/<int:fee_pk>/report/", views.report_payment, name="report_payment"),
]
