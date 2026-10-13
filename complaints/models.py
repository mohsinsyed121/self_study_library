from django.db import models


class Complaint(models.Model):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    STATUS_CHOICES = [(PENDING, "Pending"), (IN_PROGRESS, "In Progress"), (RESOLVED, "Resolved")]

    student = models.ForeignKey("students.StudentProfile", on_delete=models.PROTECT, related_name="complaints")
    subject = models.CharField(max_length=150)
    description = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)
    admin_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.subject} ({self.get_status_display()})"
