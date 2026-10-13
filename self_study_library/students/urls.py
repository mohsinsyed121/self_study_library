from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="student_dashboard"),
    path("profile/", views.profile, name="student_profile"),
    path("profile/edit/", views.profile_edit, name="student_profile_edit"),
]
