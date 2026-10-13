from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.StudentLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("continue/", views.after_login, name="after_login"),
]
