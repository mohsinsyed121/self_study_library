from django.urls import path

from . import views

urlpatterns = [
    path("", views.available_seats, name="available_seats"),
    path("my-booking/", views.my_booking, name="my_booking"),
    path("<int:pk>/", views.seat_detail, name="seat_detail"),
    path("<int:pk>/book/", views.book_seat, name="book_seat"),
    path("booking/<int:pk>/confirmation/", views.booking_confirmation, name="booking_confirmation"),
    path("booking/<int:pk>/cancel/", views.cancel_my_booking, name="cancel_my_booking"),
]
