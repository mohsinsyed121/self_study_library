from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import approved_student_required, student_required

from .models import Seat, SeatBooking
from .services import BookingError, annotate_seats, cancel_booking, request_seat, seat_counts


@student_required
def available_seats(request):
    """Visual seat layout. Seats are grouped by section for an easy-to-read map."""
    seats = annotate_seats(Seat.objects.filter(is_active=True))
    sections = {}
    for seat in seats:
        sections.setdefault(seat.section or "Main hall", []).append(seat)
    return render(request, "seats/available_seats.html", {"sections": sections, "counts": seat_counts()})


@student_required
def seat_detail(request, pk):
    seat = get_object_or_404(Seat, pk=pk, is_active=True)
    return render(request, "seats/seat_detail.html", {"seat": seat})


@approved_student_required
def book_seat(request, pk):
    """GET: show the rules and a confirm button. POST: try to book (rules are in seats/services.py)."""
    seat = get_object_or_404(Seat, pk=pk, is_active=True)
    if request.method == "POST":
        try:
            booking = request_seat(request.student, seat)
        except BookingError as error:
            messages.error(request, str(error))
            return redirect("seat_detail", pk=seat.pk)
        return redirect("booking_confirmation", pk=booking.pk)
    return render(request, "seats/book_seat.html", {"seat": seat, "membership": request.student.current_membership})


@student_required
def booking_confirmation(request, pk):
    booking = get_object_or_404(SeatBooking, pk=pk, student=request.student)  # own bookings only
    return render(request, "seats/booking_confirmation.html", {"booking": booking})


@student_required
def my_booking(request):
    history = request.student.bookings.select_related("seat")
    return render(request, "seats/my_booking.html", {"booking": request.student.active_booking, "history": history})


@student_required
@require_POST
def cancel_my_booking(request, pk):
    booking = get_object_or_404(SeatBooking, pk=pk, student=request.student)
    try:
        cancel_booking(booking)
        messages.success(request, "Your booking was cancelled.")
    except BookingError as error:
        messages.error(request, str(error))
    return redirect("my_booking")
