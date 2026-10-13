from django.urls import path

from . import admin_views as views

urlpatterns = [
    path("", views.complaint_list, name="admin_complaints"),
    path("<int:pk>/", views.complaint_detail, name="admin_complaint_detail"),
]
