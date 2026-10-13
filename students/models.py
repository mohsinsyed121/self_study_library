import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from notifications.services import notify

phone_validator = RegexValidator(r"^\+?\d{10,15}$", "Enter a valid phone number (10 to 15 digits).")


class StudentProfile(models.Model):
    """Extra information about a student. One profile per student user."""

    class Approval(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Public student number printed on the ID card, e.g. LIB00012
    student_id = models.CharField(max_length=20, unique=True, editable=False)
    # Random token placed in the QR code. It reveals nothing about the student.
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    phone = models.CharField(max_length=15, validators=[phone_validator])
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_phone = models.CharField(max_length=15, blank=True, validators=[phone_validator])
    photo = models.ImageField(upload_to="students/", blank=True)
    approval_status = models.CharField(max_length=10, choices=Approval.choices, default=Approval.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["approval_status"])]

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"

    def save(self, *args, **kwargs):
        if not self.student_id:
            # Temporary unique value, replaced with the real ID once we know the primary key.
            self.student_id = uuid.uuid4().hex[:12]
            super().save(*args, **kwargs)
            self.student_id = f"LIB{self.pk:05d}"
            super().save(update_fields=["student_id"])
        else:
            super().save(*args, **kwargs)

    # ----- simple helpers -----
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def is_approved(self):
        return self.approval_status == self.Approval.APPROVED

    @property
    def account_status(self):
        """One label for admin tables: Active / Pending / Rejected / Deactivated."""
        if not self.user.is_active:
            return "Deactivated"
        return self.get_approval_status_display() if not self.is_approved else "Active"

    @property
    def current_membership(self):
        """The active, not-yet-expired membership with the latest end date (or None)."""
        return (
            self.memberships.filter(
                status="active", start_date__lte=timezone.localdate(), end_date__gte=timezone.localdate()
            )
            .order_by("-end_date")
            .first()
        )

    @property
    def active_booking(self):
        """The reserved or allocated seat booking (a student may have only one)."""
        return self.bookings.filter(status__in=["reserved", "allocated"]).select_related("seat").first()

    def payments_queryset(self):
        """All payments made against this student's fees (newest first)."""
        from payments.models import Payment  # local import avoids circular imports

        return Payment.objects.filter(fee__student=self).select_related("fee")

    # ----- admin actions (also create notifications) -----
    def approve(self):
        self.approval_status = self.Approval.APPROVED
        self.save(update_fields=["approval_status"])
        if not self.user.is_active:
            self.user.is_active = True
            self.user.save(update_fields=["is_active"])
        notify(self.user, "Registration approved", "Your registration is approved. You can now book a seat.")

    def reject(self):
        self.approval_status = self.Approval.REJECTED
        self.save(update_fields=["approval_status"])
        notify(self.user, "Registration rejected", "Your registration was not approved. Please contact the library.")

    def deactivate(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

    def reactivate(self):
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
