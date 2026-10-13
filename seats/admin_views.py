from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.utils import paginate

from .forms import AllocateSeatForm, BulkSeatForm, ReassignSeatForm, SeatForm
from .models import Seat, SeatBooking
from .services import (BookingError, allocate_seat, annotate_seats, cancel_booking,
                       confirm_booking, reassign_booking, seat_counts)


@admin_required
def seat_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    seats = Seat.objects.all()
    if query:
        seats = seats.filter(number__icontains=query) | seats.filter(section__icontains=query)
    seats = annotate_seats(seats.order_by("number"))
    if status in ("available", "reserved", "occupied", "inactive"):
        seats = [seat for seat in seats if seat.status == status]  # status is calculated, so filter here
    return render(request, "admin_panel/seats.html", {
        "page_obj": paginate(request, seats), "counts": seat_counts(), "q": query, "status": status,
    })


@admin_required
def seat_add(request):
    form = SeatForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        seat = form.save()
        messages.success(request, f"Seat {seat.number} added.")
        return redirect("admin_seats")
    return render(request, "admin_panel/seat_form.html", {"form": form, "title": "Add seat"})


@admin_required
def seat_edit(request, pk):
    seat = get_object_or_404(Seat, pk=pk)
    form = SeatForm(request.POST or None, instance=seat)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Seat {seat.number} updated.")
        return redirect("admin_seats")
    return render(request, "admin_panel/seat_form.html", {"form": form, "title": f"Edit seat {seat.number}"})


@admin_required
def seat_bulk(request):
    form = BulkSeatForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        created = 0
        for number in range(data["start"], data["end"] + 1):
            label = f"{data['prefix'].strip().upper()}{number}"
            _, was_created = Seat.objects.get_or_create(number=label, defaults={"section": data["section"]})
            created += was_created
        messages.success(request, f"{created} new seat(s) created. Existing seat numbers were skipped.")
        return redirect("admin_seats")
    return render(request, "admin_panel/seat_form.html", {"form": form, "title": "Add many seats"})


@admin_required
def booking_list(request):
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    bookings = SeatBooking.objects.select_related("student__user", "seat")
    if status in dict(SeatBooking.STATUS_CHOICES):
        bookings = bookings.filter(status=status)
    if query:
        bookings = bookings.filter(student__student_id__icontains=query) | bookings.filter(seat__number__icontains=query) \
            | bookings.filter(student__user__first_name__icontains=query)
    return render(request, "admin_panel/bookings.html", {
        "page_obj": paginate(request, bookings), "status": status, "q": query,
        "status_choices": SeatBooking.STATUS_CHOICES,
    })


@admin_required
def allocate(request):
    initial = {"seat": request.GET.get("seat")}
    form = AllocateSeatForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            allocate_seat(form.cleaned_data["student"], form.cleaned_data["seat"], form.cleaned_data["note"])
            messages.success(request, "Seat allocated.")
            return redirect("admin_bookings")
        except BookingError as error:
            form.add_error(None, str(error))
    return render(request, "admin_panel/seat_form.html", {"form": form, "title": "Allocate a seat"})


@admin_required
def reassign(request, pk):
    booking = get_object_or_404(SeatBooking, pk=pk)
    form = ReassignSeatForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            reassign_booking(booking, form.cleaned_data["new_seat"])
            messages.success(request, "Student moved to the new seat.")
            return redirect("admin_bookings")
        except BookingError as error:
            form.add_error(None, str(error))
    return render(request, "admin_panel/seat_form.html", {
        "form": form, "title": f"Move {booking.student.full_name} (now on seat {booking.seat.number})"})


@admin_required
@require_POST
def booking_action(request, pk, action):
    booking = get_object_or_404(SeatBooking, pk=pk)
    try:
        if action == "confirm":
            confirm_booking(booking)
            messages.success(request, "Booking confirmed.")
        elif action == "cancel":
            cancel_booking(booking, by_admin=True)
            messages.success(request, "Booking cancelled.")
        else:
            messages.error(request, "Unknown action.")
    except BookingError as error:
        messages.error(request, str(error))
    return redirect("admin_bookings")
