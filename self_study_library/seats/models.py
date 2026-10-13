from django.db import models
from django.db.models import Q


class Seat(models.Model):
    """A physical study seat. The library has ONE floor, so there is no floor field."""

    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"
    INACTIVE = "inactive"

    number = models.CharField(max_length=10, unique=True)
    section = models.CharField("location / section", max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Seat {self.number}"

    @property
    def current_booking(self):
        """The reserved/allocated booking for this seat, if any (cached by annotate_seats)."""
        if not hasattr(self, "_current_booking"):
            self._current_booking = self.bookings.filter(status__in=SeatBooking.ACTIVE_STATUSES).first()
        return self._current_booking

    @property
    def status(self):
        """Status is CALCULATED from bookings, so it can never get out of sync."""
        if not self.is_active:
            return self.INACTIVE
        booking = self.current_booking
        if booking is None:
            return self.AVAILABLE
        return self.OCCUPIED if booking.status == SeatBooking.ALLOCATED else self.RESERVED

    @property
    def status_label(self):
        return self.status.capitalize()


class SeatBooking(models.Model):
    """A student's claim on a seat.

    reserved  = student requested it; held until the admin confirms (or it is cancelled)
    allocated = confirmed, the student is using the seat (seat shows as Occupied)
    cancelled / ended = history only
    """

    RESERVED = "reserved"
    ALLOCATED = "allocated"
    CANCELLED = "cancelled"
    ENDED = "ended"
    STATUS_CHOICES = [
        (RESERVED, "Reserved"),
        (ALLOCATED, "Allocated"),
        (CANCELLED, "Cancelled"),
        (ENDED, "Ended"),
    ]
    ACTIVE_STATUSES = [RESERVED, ALLOCATED]

    student = models.ForeignKey("students.StudentProfile", on_delete=models.PROTECT, related_name="bookings")
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT, related_name="bookings")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=RESERVED)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    allocated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # Database-level protection against double booking:
            # at most ONE active booking per seat ...
            models.UniqueConstraint(
                fields=["seat"], condition=Q(status__in=["reserved", "allocated"]), name="one_active_booking_per_seat"
            ),
            # ... and at most ONE active booking per student.
            models.UniqueConstraint(
                fields=["student"], condition=Q(status__in=["reserved", "allocated"]), name="one_active_booking_per_student"
            ),
        ]

    def __str__(self):
        return f"{self.student.student_id} -> {self.seat.number} ({self.status})"

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES
