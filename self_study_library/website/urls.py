from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("facilities/", views.facilities, name="facilities"),
    path("gallery/", views.gallery, name="gallery"),
    path("plans/", views.membership_plans, name="public_plans"),
    path("rules/", views.rules, name="rules"),
    path("contact/", views.contact, name="contact"),
]
