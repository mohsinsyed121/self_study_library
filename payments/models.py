from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

MONEY = dict(max_digits=10, decimal_places=2)  # DecimalField, never float, for money
MIN_AMOUNT = MinValueValidator(Decimal("0.01"))


class FeeRecord(models.Model):
    """Something the student must pay (for example a membership fee)."""

    student = models.ForeignKey("students.StudentProfile", on_delete=models.PROTECT, related_name="fees")
    membership = models.OneToOneField("memberships.Membership", null=True, blank=True, on_delete=models.PROTECT, related_name="fee")
    description = models.CharField(max_length=200)
    amount = models.DecimalField(validators=[MIN_AMOUNT], **MONEY)
    due_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(check=models.Q(amount__gt=0), name="fee_amount_positive")]

    def __str__(self):
        return f"{self.student.student_id} - {self.description} ({self.amount})"

    def _sum(self, status):
        total = self.payments.filter(status=status).aggregate(t=Sum("amount"))["t"]
        return total or Decimal("0.00")

    @property
    def total_paid(self):
        """Only CONFIRMED payments count."""
        return self._sum(Payment.CONFIRMED)

    @property
    def pending_amount(self):
        return self._sum(Payment.PENDING)

    @property
    def remaining_due(self):
        """Remaining Due = Total Fee - Confirmed Payments"""
        return self.amount - self.total_paid

    @property
    def payable_now(self):
        """How much more may still be submitted (not already covered by pending payments)."""
        return max(self.remaining_due - self.pending_amount, Decimal("0.00"))

    @property
    def payment_status(self):
        paid = self.total_paid
        if paid >= self.amount:
            return "Paid"
        return "Partial" if paid > 0 else "Unpaid"


class Payment(models.Model):
    """One payment transaction. Money is only counted once an admin has CONFIRMED it."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    STATUS_CHOICES = [(PENDING, "Pending"), (CONFIRMED, "Confirmed"), (REJECTED, "Rejected")]
    METHOD_CHOICES = [("cash", "Cash"), ("upi", "UPI"), ("bank", "Bank transfer"), ("other", "Other")]

    fee = models.ForeignKey(FeeRecord, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(validators=[MIN_AMOUNT], **MONEY)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default="cash")
    reference = models.CharField(max_length=100, blank=True, help_text="UPI / transaction / receipt reference")
    paid_on = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    receipt_number = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="payments_recorded")
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="payments_verified")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "paid_on"])]
        constraints = [models.CheckConstraint(check=models.Q(amount__gt=0), name="payment_amount_positive")]

    def __str__(self):
        return f"{self.amount} ({self.status}) for {self.fee_id}"

    @property
    def student(self):
        return self.fee.student
