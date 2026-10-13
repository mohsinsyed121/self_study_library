from django.urls import path

from . import views

urlpatterns = [
    path("", views.my_id_card, name="my_id_card"),
    path("find/", views.find_student, name="find_student"),
    path("verify/<uuid:token>/", views.verify_id_card, name="verify_id_card"),
]
