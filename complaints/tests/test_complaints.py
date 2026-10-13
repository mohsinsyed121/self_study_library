from django.test import TestCase
from django.urls import reverse

from complaints.models import Complaint
from config.test_helpers import PASSWORD, make_admin, make_student


class ComplaintTests(TestCase):
    def setUp(self):
        self.asha = make_student("asha")
        make_admin()

    def test_student_creates_complaint_as_pending(self):
        self.client.login(username="asha", password=PASSWORD)
        response = self.client.post(reverse("complaint_create"), {"subject": "Fan broken", "description": "The fan near seat 4 is broken."})
        complaint = Complaint.objects.get()
        self.assertRedirects(response, reverse("complaint_detail", args=[complaint.pk]))
        self.assertEqual(complaint.status, "pending")
        self.assertEqual(complaint.student, self.asha)

    def test_short_description_rejected(self):
        self.client.login(username="asha", password=PASSWORD)
        response = self.client.post(reverse("complaint_create"), {"subject": "Hi", "description": "short"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Complaint.objects.exists())

    def test_admin_updates_status_and_student_is_notified(self):
        complaint = Complaint.objects.create(student=self.asha, subject="Fan broken", description="The fan is broken.")
        self.client.login(username="boss", password=PASSWORD)
        self.client.post(reverse("admin_complaint_detail", args=[complaint.pk]), {"status": "in_progress", "admin_response": "We are fixing it."})
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "in_progress")
        self.assertEqual(complaint.admin_response, "We are fixing it.")
        note = self.asha.user.notifications.get(title="Complaint update")
        self.assertIn("In Progress", note.message)
        self.client.post(reverse("admin_complaint_detail", args=[complaint.pk]), {"status": "resolved", "admin_response": "Fixed."})
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "resolved")
        self.assertEqual(self.asha.user.notifications.filter(title="Complaint update").count(), 2)

    def test_student_sees_response_and_cannot_edit_status(self):
        complaint = Complaint.objects.create(student=self.asha, subject="S", description="Long enough text", admin_response="Done soon")
        self.client.login(username="asha", password=PASSWORD)
        self.assertContains(self.client.get(reverse("complaint_detail", args=[complaint.pk])), "Done soon")
        self.assertEqual(self.client.post(reverse("admin_complaint_detail", args=[complaint.pk]), {"status": "resolved"}).status_code, 403)

    def test_admin_filter(self):
        Complaint.objects.create(student=self.asha, subject="Open one", description="Long enough text")
        Complaint.objects.create(student=self.asha, subject="Closed one", description="Long enough text", status="resolved")
        self.client.login(username="boss", password=PASSWORD)
        response = self.client.get(reverse("admin_complaints") + "?status=resolved")
        self.assertContains(response, "Closed one")
        self.assertNotContains(response, "Open one")


class NotificationTests(TestCase):
    def test_mark_read_and_unread_badge(self):
        from notifications.services import notify

        asha = make_student("asha")
        note = notify(asha.user, "Hello", "World")
        self.client.login(username="asha", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("notification_list")).context["unread_count"], 1)
        self.client.post(reverse("notification_mark_read", args=[note.pk]))
        note.refresh_from_db()
        self.assertTrue(note.is_read)
        notify(asha.user, "Two", "x")
        self.client.post(reverse("notification_mark_all_read"))
        self.assertFalse(asha.user.notifications.filter(is_read=False).exists())

    def test_approval_and_rejection_create_notifications(self):
        pending = make_student("pend", approved=False)
        pending.approve()
        pending.reject()
        titles = set(pending.user.notifications.values_list("title", flat=True))
        self.assertEqual(titles, {"Registration approved", "Registration rejected"})
