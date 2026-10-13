"""All seat-booking business rules live here, so views and tests share ONE copy of the logic."""
from django.db import IntegrityError, transaction
from django.utils import timezone

from notifications.services import notify

from .models import Seat, SeatBooking


class BookingError(Exception):
    """Raised when a booking rule is broken. The message is safe to show to the user."""


def annotate_seats(seats):
    """Attach the current booking to each seat using ONE query (instead of one per seat)."""
    seats = list(seats)
    active = SeatBooking.objects.filter(
        seat__in=seats, status__in=SeatBooking.ACTIVE_STATUSES
    ).select_related("student__user")
    by_seat = {booking.seat_id: booking for booking in active}
    for seat in seats:
        seat._current_booking = by_seat.get(seat.id)
    return seats


def seat_counts():
    """Counts used on the home page and dashboards."""
    active_seats = Seat.objects.filter(is_active=True)
    total = active_seats.count()
    allocated = SeatBooking.objects.filter(status=SeatBooking.ALLOCATED, seat__is_active=True).count()
    reserved = SeatBooking.objects.filter(status=SeatBooking.RESERVED, seat__is_active=True).count()
    return {
        "total": total,
        "occupied": allocated,
        "reserved": reserved,
        "available": total - allocated - reserved,
        "inactive": Seat.objects.filter(is_active=False).count(),
    }


def _lock_seat(seat):
    """Lock the seat row while we check it (works on PostgreSQL; SQLite ignores it)."""
    return Seat.objects.select_for_update().get(pk=seat.pk)


def _check_seat_free(seat):
    if not seat.is_active:
        raise BookingError(f"Seat {seat.number} is not in service.")
    if SeatBooking.objects.filter(seat=seat, status__in=SeatBooking.ACTIVE_STATUSES).exists():
        raise BookingError(f"Seat {seat.number} is already taken. Please choose another seat.")


def _check_student_free(student):
    if SeatBooking.objects.filter(student=student, status__in=SeatBooking.ACTIVE_STATUSES).exists():
        raise BookingError("You already have a seat. Cancel it first if you want a different one.")


def _create_booking(student, seat, status, note=""):
    try:
        with transaction.atomic():
            return SeatBooking.objects.create(
                student=student,
                seat=seat,
                status=status,
                note=note,
                allocated_at=timezone.now() if status == SeatBooking.ALLOCATED else None,
            )
    except IntegrityError:
        # Another request won the race; the database constraint stopped us.
        raise BookingError("Sorry, that seat was just taken. Please choose another seat.")


@transaction.atomic
def request_seat(student, seat):
    """Student books a seat. Rules: approved + active membership + no other seat + seat free."""
    seat = _lock_seat(seat)
    if not student.is_approved:
        raise BookingError("Your registration must be approved before you can book a seat.")
    if student.current_membership is None:
        raise BookingError("You need an active membership to book a seat.")
    _check_student_free(student)
    _check_seat_free(seat)
    booking = _create_booking(student, seat, SeatBooking.RESERVED)
    notify(student.user, "Seat reserved", f"Seat {seat.number} is reserved for you. The library will confirm it.")
    return booking


@transaction.atomic
def allocate_seat(student, seat, note=""):
    """Admin gives a seat to a student directly (confirmed immediately)."""
    seat = _lock_seat(seat)
    if not student.is_approved:
        raise BookingError("Only approved students can be given a seat.")
    _check_student_free(student)
    _check_seat_free(seat)
    booking = _create_booking(student, seat, SeatBooking.ALLOCATED, note)
    notify(student.user, "Seat allocated", f"Seat {seat.number} has been allocated to you.")
    return booking


@transaction.atomic
def confirm_booking(booking):
    booking = SeatBooking.objects.select_for_update().get(pk=booking.pk)
    if booking.status != SeatBooking.RESERVED:
        raise BookingError("Only reserved bookings can be confirmed.")
    booking.status = SeatBooking.ALLOCATED
    booking.allocated_at = timezone.now()
    booking.save(update_fields=["status", "allocated_at"])
    notify(booking.student.user, "Booking confirmed", f"Seat {booking.seat.number} is confirmed for you.")
    return booking


@transaction.atomic
def cancel_booking(booking, by_admin=False):
    booking = SeatBooking.objects.select_for_update().get(pk=booking.pk)
    if not booking.is_active:
        raise BookingError("This booking is already closed.")
    booking.status = SeatBooking.CANCELLED
    booking.closed_at = timezone.now()
    booking.save(update_fields=["status", "closed_at"])
    who = "the library" if by_admin else "you"
    notify(booking.student.user, "Booking cancelled", f"Your booking for seat {booking.seat.number} was cancelled by {who}.")
    return booking


@transaction.atomic
def end_booking(booking, reason="Ended"):
    """Close an allocated booking normally (for example when the membership expires)."""
    booking = SeatBooking.objects.select_for_update().get(pk=booking.pk)
    if not booking.is_active:
        return booking
    booking.status = SeatBooking.ENDED
    booking.note = reason
    booking.closed_at = timezone.now()
    booking.save(update_fields=["status", "note", "closed_at"])
    notify(booking.student.user, "Seat released", f"Seat {booking.seat.number} was released: {reason.lower()}.")
    return booking


@transaction.atomic
def reassign_booking(booking, new_seat):
    """Move a student to another seat. The old booking stays in history as 'ended'."""
    booking = SeatBooking.objects.select_for_update().get(pk=booking.pk)
    new_seat = _lock_seat(new_seat)
    if not booking.is_active:
        raise BookingError("Only active bookings can be moved.")
    if new_seat.pk == booking.seat_id:
        raise BookingError("The student is already on that seat.")
    _check_seat_free(new_seat)
    old_seat, student, old_status = booking.seat, booking.student, booking.status
    # Close the old booking FIRST so the unique constraints are never violated.
    booking.status = SeatBooking.ENDED
    booking.note = f"Moved to seat {new_seat.number}"
    booking.closed_at = timezone.now()
    booking.save(update_fields=["status", "note", "closed_at"])
    new_booking = _create_booking(student, new_seat, old_status, f"Moved from seat {old_seat.number}")
    if old_status == SeatBooking.ALLOCATED:
        new_booking.allocated_at = timezone.now()
        new_booking.save(update_fields=["allocated_at"])
    notify(student.user, "Seat changed", f"Your seat was changed from {old_seat.number} to {new_seat.number}.")
    return new_booking
