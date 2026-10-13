from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from config.test_helpers import PASSWORD, make_admin, make_student
from students.models import StudentProfile


class RegistrationTests(TestCase):
    data = {"username": "newbie", "first_name": "New", "last_name": "Student", "email": "new@example.com",
            "phone": "9876543210", "address": "Lucknow", "password1": PASSWORD, "password2": PASSWORD}

    def test_register_creates_user_and_pending_profile(self):
        response = self.client.post(reverse("register"), self.data)
        self.assertRedirects(response, reverse("student_dashboard"))
        profile = StudentProfile.objects.get(user__username="newbie")
        self.assertEqual(profile.approval_status, "pending")
        self.assertTrue(profile.student_id.startswith("LIB"))
        self.assertEqual(profile.user.notifications.count(), 1)

    def test_duplicate_email_rejected(self):
        make_student("existing")
        data = dict(self.data, email="existing@example.com")
        response = self.client.post(reverse("register"), data)
        self.assertContains(response, "already exists")
        self.assertFalse(User.objects.filter(username="newbie").exists())

    def test_bad_phone_and_weak_password_rejected(self):
        response = self.client.post(reverse("register"), dict(self.data, phone="abc", password1="123", password2="123"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors.get("phone"))
        self.assertTrue(response.context["form"].errors.get("password2"))
        self.assertEqual(User.objects.count(), 0)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.admin = make_admin()

    def test_student_login_goes_to_student_dashboard(self):
        response = self.client.post(reverse("login"), {"username": "asha", "password": PASSWORD})
        self.assertRedirects(response, "/student/")

    def test_admin_login_goes_to_admin_dashboard(self):
        response = self.client.post(reverse("login"), {"username": "boss", "password": PASSWORD})
        self.assertRedirects(response, "/manage/")

    def test_wrong_password(self):
        response = self.client.post(reverse("login"), {"username": "asha", "password": "nope"})
        self.assertContains(response, "Wrong username or password")

    def test_deactivated_user_cannot_login(self):
        self.student.deactivate()
        response = self.client.post(reverse("login"), {"username": "asha", "password": PASSWORD})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(response.status_code, 200)

    def test_logout_ends_session_and_dashboard_is_protected(self):
        self.client.login(username="asha", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 200)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.get(reverse("student_dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next=/student/")

    def test_logout_requires_post(self):
        self.client.login(username="asha", password=PASSWORD)
        self.client.get(reverse("logout"))  # only shows the confirmation page
        self.assertIn("_auth_user_id", self.client.session)

    def test_private_pages_send_no_cache_headers(self):
        self.client.login(username="asha", password=PASSWORD)
        for name in ("student_dashboard", "student_profile", "fee_summary"):
            cache = self.client.get(reverse(name))["Cache-Control"]
            self.assertIn("no-store", cache, name)
        self.client.login(username="boss", password=PASSWORD)
        self.assertIn("no-store", self.client.get(reverse("admin_dashboard"))["Cache-Control"])


class PermissionTests(TestCase):
    def setUp(self):
        self.student = make_student()
        make_admin()

    def test_anonymous_is_redirected_to_login(self):
        for name in ("student_dashboard", "available_seats", "fee_summary", "my_id_card", "admin_dashboard", "admin_students"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn(reverse("login"), response["Location"])

    def test_student_gets_403_on_every_admin_page(self):
        self.client.login(username="asha", password=PASSWORD)
        for name in ("admin_dashboard", "admin_students", "admin_seats", "admin_bookings", "admin_plans", "admin_memberships",
                     "admin_fees", "admin_payments", "admin_complaints", "admin_reports", "admin_settings", "find_student"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_student_cannot_run_admin_actions(self):
        self.client.login(username="asha", password=PASSWORD)
        response = self.client.post(reverse("admin_student_action", args=[self.student.pk, "deactivate"]))
        self.assertEqual(response.status_code, 403)

    def test_admin_is_sent_away_from_student_pages(self):
        self.client.login(username="boss", password=PASSWORD)
        self.assertRedirects(self.client.get(reverse("student_dashboard")), reverse("admin_dashboard"))

    def test_pending_student_cannot_book_or_complain(self):
        pending = make_student("pending_p", approved=False)
        self.client.login(username="pending_p", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("complaint_create")).status_code, 302)
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 200)
