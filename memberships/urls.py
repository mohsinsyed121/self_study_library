from django.urls import path

from . import views

urlpatterns = [
    path("plans/", views.plans, name="plans"),
    path("my/", views.my_membership, name="my_membership"),
    path("renew/", views.renew, name="renew_membership"),
    path("request/<int:pk>/cancel/", views.cancel_request, name="cancel_membership_request"),
]
