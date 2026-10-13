from django.urls import path

from . import admin_views as views

urlpatterns = [
    path("settings/", views.settings_view, name="admin_settings"),
    path("enquiries/", views.enquiry_list, name="admin_enquiries"),
    path("enquiries/<int:pk>/handled/", views.enquiry_handled, name="admin_enquiry_handled"),
]
