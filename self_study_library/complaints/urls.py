from django.urls import path

from . import views

urlpatterns = [
    path("", views.complaint_list, name="complaint_list"),
    path("new/", views.complaint_create, name="complaint_create"),
    path("<int:pk>/", views.complaint_detail, name="complaint_detail"),
]
