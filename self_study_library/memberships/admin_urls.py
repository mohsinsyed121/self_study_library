from django.urls import path

from . import admin_views as views

urlpatterns = [
    path("", views.membership_list, name="admin_memberships"),
    path("add/", views.membership_add, name="admin_membership_add"),
    path("<int:pk>/<str:action>/", views.membership_action, name="admin_membership_action"),
    path("plans/", views.plan_list, name="admin_plans"),
    path("plans/add/", views.plan_add, name="admin_plan_add"),
    path("plans/<int:pk>/edit/", views.plan_edit, name="admin_plan_edit"),
]
