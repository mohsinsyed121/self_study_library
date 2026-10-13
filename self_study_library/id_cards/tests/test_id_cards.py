from django.test import TestCase
from django.urls import reverse

from config.test_helpers import PASSWORD, make_admin, make_member, make_student


class IdCardTests(TestCase):
    def setUp(self):
        self.asha, _ = make_member("asha")
        self.ravi = make_student("ravi")
        make_admin()

    def test_card_shows_details_and_qr_image(self):
        self.client.login(username="asha", password=PASSWORD)
        response = self.client.get(reverse("my_id_card"))
        self.assertContains(response, self.asha.student_id)
        self.assertContains(response, "Asha Test")
        self.assertContains(response, "data:image/png;base64,")
        self.assertContains(response, "Active")

    def test_qr_holds_only_verification_link(self):
        from id_cards import views

        captured = {}
        original = views.qr_data_uri
        views.qr_data_uri = lambda text: captured.setdefault("text", text) and "data:image/png;base64,AA=="
        try:
            self.client.login(username="asha", password=PASSWORD)
            self.client.get(reverse("my_id_card"))
        finally:
            views.qr_data_uri = original
        text = captured["text"]
        self.assertIn(str(self.asha.qr_token), text)
        for private in ("9876543210", "asha@example.com", "1000", "Asha"):
            self.assertNotIn(private, text)

    def test_qr_token_is_unique_and_not_the_student_id(self):
        self.assertNotEqual(self.asha.qr_token, self.ravi.qr_token)
        self.assertNotIn(self.asha.student_id, str(self.asha.qr_token))

    def test_verify_page_admin_only(self):
        url = reverse("verify_id_card", args=[self.asha.qr_token])
        self.assertEqual(self.client.get(url).status_code, 302)           # anonymous -> login
        self.client.login(username="ravi", password=PASSWORD)
        self.assertEqual(self.client.get(url).status_code, 403)           # student -> forbidden
        self.client.login(username="boss", password=PASSWORD)
        response = self.client.get(url)
        self.assertContains(response, self.asha.student_id)
        self.assertContains(response, "Active")

    def test_verify_unknown_token_is_404(self):
        self.client.login(username="boss", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("verify_id_card", args=["00000000-0000-0000-0000-000000000000"])).status_code, 404)

    def test_manual_lookup(self):
        self.client.login(username="boss", password=PASSWORD)
        response = self.client.post(reverse("find_student"), {"student_id": self.asha.student_id.lower()})
        self.assertRedirects(response, reverse("verify_id_card", args=[self.asha.qr_token]))
        self.assertContains(self.client.post(reverse("find_student"), {"student_id": "NOPE"}), "No student found")
