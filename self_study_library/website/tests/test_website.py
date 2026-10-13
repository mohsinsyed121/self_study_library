from datetime import time

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from config.test_helpers import PASSWORD, make_admin, make_plan, make_seat, make_student
from website.models import ContactEnquiry, SiteSettings


class PublicPageTests(TestCase):
    def test_all_public_pages_load(self):
        for name in ("home", "about", "facilities", "gallery", "public_plans", "rules", "contact", "login", "register"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_home_shows_real_seat_count_plans_and_timings(self):
        make_seat("A1"); make_seat("A2")
        make_plan("Monthly", 30, "999.00")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["counts"]["available"], 2)
        self.assertContains(response, "Monthly")
        self.assertContains(response, "06:00 AM")

    def test_contact_form_saves_enquiry_and_validates(self):
        self.client.post(reverse("contact"), {"name": "Visitor", "email": "v@example.com", "message": "Is there parking?"})
        self.assertEqual(ContactEnquiry.objects.get().name, "Visitor")
        response = self.client.post(reverse("contact"), {"name": "", "email": "bad", "message": ""})
        self.assertEqual(ContactEnquiry.objects.count(), 1)
        self.assertTrue(response.context["form"].errors)

    def test_custom_404_page(self):
        response = self.client.get("/definitely/not/here/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "errors/404.html")

    def test_403_page_is_custom(self):
        make_student("asha")
        self.client.login(username="asha", password=PASSWORD)
        self.assertTemplateUsed(self.client.get(reverse("admin_dashboard")), "errors/403.html")


class SiteSettingsTests(TestCase):
    def setUp(self):
        make_admin()
        self.client.login(username="boss", password=PASSWORD)

    def test_admin_updates_settings_and_public_site_changes(self):
        data = {"library_name": "Quiet Corner", "tagline": "Study well", "about_text": "About us", "address": "12 Park Road",
                "phone": "9876500000", "email": "hello@quiet.in", "opening_time": "07:00", "closing_time": "21:30",
                "rules": "Be silent\nBe kind"}
        response = self.client.post(reverse("admin_settings"), data)
        self.assertRedirects(response, reverse("admin_settings"))
        site = SiteSettings.load()
        self.assertEqual(site.library_name, "Quiet Corner")
        self.assertEqual(site.closing_time, time(21, 30))
        self.client.logout()
        self.assertContains(self.client.get(reverse("rules")), "Be kind")
        self.assertContains(self.client.get(reverse("home")), "Quiet Corner")

    def test_closing_before_opening_rejected(self):
        data = {"library_name": "X", "tagline": "t", "about_text": "a", "address": "a", "phone": "1", "email": "a@b.co",
                "opening_time": "10:00", "closing_time": "09:00", "rules": "r"}
        response = self.client.post(reverse("admin_settings"), data)
        self.assertContains(response, "Closing time must be after opening time")

    def test_only_one_settings_row(self):
        SiteSettings.load(); SiteSettings.load()
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_logo_upload(self):
        import tempfile
        from PIL import Image
        from io import BytesIO
        buffer = BytesIO(); Image.new("RGB", (10, 10), "red").save(buffer, "PNG")
        data = {"library_name": "X", "tagline": "t", "about_text": "a", "address": "a", "phone": "1", "email": "a@b.co",
                "opening_time": "06:00", "closing_time": "22:00", "rules": "r",
                "logo": SimpleUploadedFile("logo.png", buffer.getvalue(), content_type="image/png")}
        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            self.client.post(reverse("admin_settings"), data)
            self.assertTrue(SiteSettings.load().logo.name.endswith(".png"))
