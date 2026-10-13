"""A student must never reach another student's private records by changing an ID in the URL."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from complaints.models import Complaint
from config.test_helpers import PASSWORD, make_admin, make_member, make_seat
from notifications.services import notify
from payments.services import record_payment
from seats.services import allocate_seat
import datetime


class StudentIsolationTests(TestCase):
    def setUp(self):
        self.asha, self.asha_membership = make_member("asha")
        self.ravi, self.ravi_membership = make_member("ravi")
        admin = make_admin()
        self.ravi_payment = record_payment(self.ravi_membership.fee, Decimal("100"), "cash", "SECRETREF", datetime.date.today(), admin)
        self.ravi_booking = allocate_seat(self.ravi, make_seat("R1"))
        self.ravi_complaint = Complaint.objects.create(student=self.ravi, subject="Ravi private", description="private text here")
        self.ravi_note = notify(self.ravi.user, "Ravi only", "secret")
        self.client.login(username="asha", password=PASSWORD)

    def test_other_students_records_return_404(self):
        urls = [
            reverse("payment_detail", args=[self.ravi_payment.pk]),
            reverse("payment_receipt", args=[self.ravi_payment.pk]),
            reverse("booking_confirmation", args=[self.ravi_booking.pk]),
            reverse("complaint_detail", args=[self.ravi_complaint.pk]),
            reverse("report_payment", args=[self.ravi_membership.fee.pk]),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_cannot_mark_other_students_notification_read(self):
        response = self.client.post(reverse("notification_mark_read", args=[self.ravi_note.pk]))
        self.assertEqual(response.status_code, 404)
        self.ravi_note.refresh_from_db()
        self.assertFalse(self.ravi_note.is_read)

    def test_lists_only_show_own_data(self):
        self.assertNotContains(self.client.get(reverse("payment_history")), "Ravi")
        self.assertNotContains(self.client.get(reverse("complaint_list")), "Ravi private")
        self.assertNotContains(self.client.get(reverse("notification_list")), "Ravi only")
        self.assertNotContains(self.client.get(reverse("fee_summary")), "ravi".title())
        self.assertNotContains(self.client.get(reverse("student_dashboard")), "Ravi")

    def test_cannot_fake_owner_when_creating_complaint(self):
        self.client.post(reverse("complaint_create"), {"subject": "Noise", "description": "It is very noisy here",
                                                      "student": self.ravi.pk})
        self.assertEqual(Complaint.objects.get(subject="Noise").student, self.asha)

    def test_profile_edit_cannot_change_protected_fields(self):
        original_id = self.asha.student_id
        self.client.post(reverse("student_profile_edit"), {
            "first_name": "Asha", "last_name": "New", "email": "asha@example.com", "phone": "9999999999",
            "student_id": "HACKED", "approval_status": "rejected", "qr_token": "1"})
        self.asha.refresh_from_db()
        self.assertEqual(self.asha.student_id, original_id)
        self.assertEqual(self.asha.approval_status, "approved")
        self.assertEqual(self.asha.phone, "9999999999")
        self.assertEqual(self.asha.user.last_name, "New")

    def test_profile_edit_validation(self):
        response = self.client.post(reverse("student_profile_edit"), {
            "first_name": "Asha", "last_name": "T", "email": "ravi@example.com", "phone": "12"})
        self.assertEqual(response.status_code, 200)
        errors = response.context["form"].errors
        self.assertIn("email", errors)
        self.assertIn("phone", errors)
