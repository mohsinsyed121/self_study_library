"""Membership rules: request, activate, renew, expire."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from notifications.services import notify
from payments.models import FeeRecord

from .models import Membership


class MembershipError(Exception):
    """A membership rule was broken; the message is safe to show to the user."""


def request_membership(student, plan):
    """Student asks for a plan (or a renewal). It stays 'pending' until the admin activates it."""
    if not student.is_approved:
        raise MembershipError("Your registration must be approved first.")
    if not plan.is_active:
        raise MembershipError("This plan is not available.")
    if student.memberships.filter(status=Membership.PENDING).exists():
        raise MembershipError("You already have a pending membership request.")
    return Membership.objects.create(student=student, plan=plan, price=plan.price)


@transaction.atomic
def activate_membership(membership):
    """Set dates, mark active and create the fee record.

    If the student is still active, the new period starts the day AFTER the current one ends
    (renewal), so no paid days are lost.
    """
    membership = Membership.objects.select_for_update().get(pk=membership.pk)
    if membership.status != Membership.PENDING:
        raise MembershipError("Only pending memberships can be activated.")
    today = timezone.localdate()
    latest = (
        Membership.objects.filter(student=membership.student, status=Membership.ACTIVE, end_date__gte=today)
        .order_by("-end_date")
        .first()
    )
    start = latest.end_date + timedelta(days=1) if latest else today
    membership.start_date = start
    membership.end_date = start + timedelta(days=membership.plan.duration_days - 1)
    membership.status = Membership.ACTIVE
    membership.save(update_fields=["start_date", "end_date", "status"])
    FeeRecord.objects.create(
        student=membership.student,
        membership=membership,
        description=f"{membership.plan.name} membership ({start:%d %b %Y} to {membership.end_date:%d %b %Y})",
        amount=membership.price,
        due_date=start,
    )
    notify(
        membership.student.user,
        "Membership activated",
        f"Your {membership.plan.name} membership is active until {membership.end_date:%d %b %Y}.",
    )
    return membership


def create_and_activate(student, plan):
    """Admin shortcut: create a membership and activate it immediately."""
    membership = Membership.objects.create(student=student, plan=plan, price=plan.price)
    return activate_membership(membership)


def cancel_membership(membership):
    if membership.status != Membership.PENDING:
        raise MembershipError("Only pending requests can be cancelled. Active memberships expire on their end date.")
    membership.status = Membership.CANCELLED
    membership.save(update_fields=["status"])
    return membership


def expire_overdue_memberships(today=None):
    """Mark memberships whose end date has passed as expired and release seats.

    Safe to run many times. Called from the admin dashboard and the
    `python manage.py expire_memberships` command (run it daily).
    """
    from seats.models import SeatBooking  # local import avoids circular imports
    from seats.services import end_booking

    today = today or timezone.localdate()
    overdue = Membership.objects.filter(status=Membership.ACTIVE, end_date__lt=today).select_related("student__user")
    count = 0
    for membership in overdue:
        membership.status = Membership.EXPIRED
        membership.save(update_fields=["status"])
        notify(membership.student.user, "Membership expired", f"Your {membership.plan.name} membership expired on {membership.end_date:%d %b %Y}. Please renew.")
        count += 1
        student = membership.student
        still_active = student.memberships.filter(status=Membership.ACTIVE, end_date__gte=today).exists()
        if not still_active:
            for booking in student.bookings.filter(status__in=SeatBooking.ACTIVE_STATUSES):
                end_booking(booking, reason="Membership expired")
    return count
