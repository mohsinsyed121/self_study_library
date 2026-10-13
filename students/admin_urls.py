from django.urls import path

from . import admin_views as views

urlpatterns = [
    path("", views.student_list, name="admin_students"),
    path("<int:pk>/", views.student_detail, name="admin_student_detail"),
    path("<int:pk>/<str:action>/", views.student_action, name="admin_student_action"),
]
