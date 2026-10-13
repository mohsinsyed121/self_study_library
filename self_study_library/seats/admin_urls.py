from django.urls import path

from . import admin_views as views

urlpatterns = [
    path("", views.seat_list, name="admin_seats"),
    path("add/", views.seat_add, name="admin_seat_add"),
    path("bulk/", views.seat_bulk, name="admin_seat_bulk"),
    path("<int:pk>/edit/", views.seat_edit, name="admin_seat_edit"),
    path("bookings/", views.booking_list, name="admin_bookings"),
    path("allocate/", views.allocate, name="admin_allocate"),
    path("bookings/<int:pk>/move/", views.reassign, name="admin_reassign"),
    path("bookings/<int:pk>/<str:action>/", views.booking_action, name="admin_booking_action"),
]
