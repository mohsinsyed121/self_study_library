from django.urls import path
from . import admin_setup
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.StudentLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("continue/", views.after_login, name="after_login"),
    path(
    "__temporary-admin-setup/",
    admin_setup.create_temporary_admin,
    name="temporary_admin_setup",
),
]
