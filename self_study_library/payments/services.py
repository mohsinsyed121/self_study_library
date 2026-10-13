"""Payment rules. There is NO online gateway: students report payments, admins verify them."""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from notifications.services import notify

from .models import FeeRecord, Payment


class PaymentError(Exception):
    """A payment rule was broken; the message is safe to show to the user."""


def fee_summary_for(student):
    """Totals for one student, always calculated from the database."""
    zero = Decimal("0.00")
    total_fee = student.fees.aggregate(t=Sum("amount"))["t"] or zero
    total_paid = Payment.objects.filter(fee__student=student, status=Payment.CONFIRMED).aggregate(t=Sum("amount"))["t"] or zero
    pending = Payment.objects.filter(fee__student=student, status=Payment.PENDING).aggregate(t=Sum("amount"))["t"] or zero
    return {
        "total_fee": total_fee,
        "total_paid": total_paid,
        "remaining_due": total_fee - total_paid,  # Remaining Due = Total Fee - Confirmed Payments
        "pending_verification": pending,
    }


def _validate_amount(amount, limit):
    if amount is None or amount <= 0:
        raise PaymentError("Payment amount must be greater than zero.")
    if amount > limit:
        raise PaymentError(f"Amount is more than the balance that can still be paid (Rs. {limit}).")


@transaction.atomic
def submit_payment(fee, amount, method, reference, paid_on, user):
    """Student reports a payment they made. Saved as PENDING until the admin verifies it."""
    fee = FeeRecord.objects.select_for_update().get(pk=fee.pk)
    _validate_amount(amount, fee.payable_now)
    return Payment.objects.create(
        fee=fee, amount=amount, method=method, reference=reference,
        paid_on=paid_on, status=Payment.PENDING, recorded_by=user,
    )


@transaction.atomic
def record_payment(fee, amount, method, reference, paid_on, admin_user, confirm=True):
    """Admin records a payment, and confirms it straight away unless told not to."""
    fee = FeeRecord.objects.select_for_update().get(pk=fee.pk)
    limit = fee.remaining_due if confirm else fee.payable_now
    _validate_amount(amount, limit)
    payment = Payment.objects.create(
        fee=fee, amount=amount, method=method, reference=reference,
        paid_on=paid_on, status=Payment.PENDING, recorded_by=admin_user,
    )
    if confirm:
        confirm_payment(payment, admin_user)
        payment.refresh_from_db()  # pick up the receipt number and status set while confirming
    return payment


@transaction.atomic
def confirm_payment(payment, admin_user):
    payment = Payment.objects.select_for_update().select_related("fee__student__user").get(pk=payment.pk)
    if payment.status != Payment.PENDING:
        raise PaymentError("Only pending payments can be confirmed.")
    fee = FeeRecord.objects.select_for_update().get(pk=payment.fee_id)
    if payment.amount > fee.remaining_due:  # re-check: other payments may have been confirmed meanwhile
        raise PaymentError("Confirming this would collect more than the fee. Reject it or fix the amount.")
    payment.status = Payment.CONFIRMED
    payment.verified_by = admin_user
    payment.verified_at = timezone.now()
    payment.receipt_number = f"RCP{timezone.localdate():%y%m}{payment.pk:06d}"
    payment.save(update_fields=["status", "verified_by", "verified_at", "receipt_number"])
    notify(payment.fee.student.user, "Payment confirmed", f"Your payment of Rs. {payment.amount} was confirmed. Receipt: {payment.receipt_number}.")
    return payment


@transaction.atomic
def reject_payment(payment, admin_user):
    payment = Payment.objects.select_for_update().select_related("fee__student__user").get(pk=payment.pk)
    if payment.status != Payment.PENDING:
        raise PaymentError("Only pending payments can be rejected.")
    payment.status = Payment.REJECTED
    payment.verified_by = admin_user
    payment.verified_at = timezone.now()
    payment.save(update_fields=["status", "verified_by", "verified_at"])
    notify(payment.fee.student.user, "Payment rejected", f"Your reported payment of Rs. {payment.amount} could not be verified. Please contact the library.")
    return payment
