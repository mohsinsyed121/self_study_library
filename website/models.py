from datetime import time

from django.db import models


class SiteSettings(models.Model):
    """One row of editable website settings (the admin edits this in Website Settings)."""

    library_name = models.CharField(max_length=100, default="Self-Study Library")
    tagline = models.CharField(max_length=200, default="A quiet place to focus, every day.")
    logo = models.ImageField(upload_to="site/", blank=True)
    about_text = models.TextField(default="We are a single-floor self-study library for students preparing for exams and learning on their own.")
    address = models.TextField(default="Your library address here")
    phone = models.CharField(max_length=20, default="+91 00000 00000")
    email = models.EmailField(default="library@example.com")
    opening_time = models.TimeField(default=time(6, 0))
    closing_time = models.TimeField(default=time(22, 0))
    rules = models.TextField(default="Keep silence.\nKeep your seat clean.\nCarry your QR ID card.\nNo food at the study desks.")

    class Meta:
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.library_name

    @classmethod
    def load(cls):
        """Return the single settings row, creating it with defaults the first time."""
        obj = cls.objects.first()
        return obj or cls.objects.create()

    @property
    def rules_list(self):
        return [line.strip() for line in self.rules.splitlines() if line.strip()]


class ContactEnquiry(models.Model):
    """A message sent from the public Contact page."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    is_handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Contact enquiries"

    def __str__(self):
        return f"{self.name} - {self.created_at:%d %b %Y}"
