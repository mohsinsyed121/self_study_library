from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class MembershipPlan(models.Model):
    name = models.CharField(max_length=80, unique=True)
    duration_days = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text="How many days the plan lasts")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["duration_days", "price"]

    def __str__(self):
        return f"{self.name} ({self.duration_days} days)"


class Membership(models.Model):
    """One membership period. Renewing creates a NEW row, so history is kept."""

    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [(PENDING, "Pending"), (ACTIVE, "Active"), (EXPIRED, "Expired"), (CANCELLED, "Cancelled")]

    student = models.ForeignKey("students.StudentProfile", on_delete=models.PROTECT, related_name="memberships")
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name="memberships")
    # Price is copied from the plan so later plan price changes do not rewrite history.
    price = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "end_date"])]
        constraints = [
            models.CheckConstraint(check=models.Q(price__gte=0), name="membership_price_not_negative"),
        ]

    def __str__(self):
        return f"{self.student.student_id} - {self.plan.name} ({self.status})"

    @property
    def days_left(self):
        if self.status != self.ACTIVE or not self.end_date:
            return 0
        return max((self.end_date - timezone.localdate()).days, 0)

    @property
    def is_current(self):
        today = timezone.localdate()
        return self.status == self.ACTIVE and self.start_date <= today <= self.end_date
