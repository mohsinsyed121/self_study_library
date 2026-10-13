from django.test import TestCase
from django.urls import reverse

from config.test_helpers import PASSWORD, make_admin, make_member, make_plan, make_seat, make_student
from memberships.models import MembershipPlan
from seats.models import Seat, SeatBooking
from seats.services import allocate_seat, request_seat


class AdminSeatTests(TestCase):
    def setUp(self):
        make_admin()
        self.client.login(username="boss", password=PASSWORD)

    def test_add_edit_and_unique_seat_number(self):
        self.client.post(reverse("admin_seat_add"), {"number": "a1", "section": "Front", "is_active": "on"})
        seat = Seat.objects.get()
        self.assertEqual(seat.number, "A1")
        response = self.client.post(reverse("admin_seat_add"), {"number": "A1", "is_active": "on"})
        self.assertEqual(Seat.objects.count(), 1)
        self.assertTrue(response.context["form"].errors)
        self.client.post(reverse("admin_seat_edit", args=[seat.pk]), {"number": "A1", "section": "Back", "is_active": "on"})
        seat.refresh_from_db()
        self.assertEqual(seat.section, "Back")

    def test_bulk_create_skips_existing(self):
        make_seat("A2")
        self.client.post(reverse("admin_seat_bulk"), {"prefix": "a", "start": 1, "end": 4, "section": "Hall"})
        self.assertEqual(sorted(Seat.objects.values_list("number", flat=True)), ["A1", "A2", "A3", "A4"])
        response = self.client.post(reverse("admin_seat_bulk"), {"prefix": "", "start": 5, "end": 2})
        self.assertTrue(response.context["form"].errors)

    def test_cannot_deactivate_seat_in_use(self):
        student, _ = make_member("asha")
        seat = make_seat("A1")
        allocate_seat(student, seat)
        response = self.client.post(reverse("admin_seat_edit", args=[seat.pk]), {"number": "A1"})  # is_active missing = off
        seat.refresh_from_db()
        self.assertTrue(seat.is_active)
        self.assertContains(response, "active booking")

    def test_deactivated_seat_hidden_from_students(self):
        seat = make_seat("A1")
        self.client.post(reverse("admin_seat_edit", args=[seat.pk]), {"number": "A1"})
        seat.refresh_from_db()
        self.assertEqual(seat.status, "inactive")
        make_student("asha")
        self.client.login(username="asha", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("seat_detail", args=[seat.pk])).status_code, 404)

    def test_admin_allocate_confirm_move_cancel(self):
        student, _ = make_member("asha")
        s1, s2 = make_seat("A1"), make_seat("A2")
        self.client.post(reverse("admin_allocate"), {"student": student.pk, "seat": s1.pk, "note": ""})
        booking = SeatBooking.objects.get()
        self.assertEqual(booking.status, "allocated")
        self.client.post(reverse("admin_reassign", args=[booking.pk]), {"new_seat": s2.pk})
        self.assertEqual(student.active_booking.seat, s2)
        self.client.post(reverse("admin_booking_action", args=[student.active_booking.pk, "cancel"]))
        self.assertIsNone(student.active_booking)
        self.assertEqual(SeatBooking.objects.count(), 2)

    def test_admin_confirms_student_reservation(self):
        student, _ = make_member("asha")
        booking = request_seat(student, make_seat("A1"))
        self.client.post(reverse("admin_booking_action", args=[booking.pk, "confirm"]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, "allocated")
        self.assertTrue(student.user.notifications.filter(title="Booking confirmed").exists())

    def test_allocating_taken_seat_shows_error(self):
        a, _ = make_member("asha"); b, _ = make_member("ravi")
        seat = make_seat("A1")
        allocate_seat(a, seat)
        response = self.client.post(reverse("admin_allocate"), {"student": b.pk, "seat": seat.pk, "note": ""})
        self.assertContains(response, "already taken")

    def test_seat_list_filter_and_pagination_pages(self):
        for i in range(20):
            make_seat(f"S{i:02d}")
        self.assertEqual(len(self.client.get(reverse("admin_seats")).context["page_obj"]), 15)
        self.assertEqual(len(self.client.get(reverse("admin_seats") + "?page=2").context["page_obj"]), 5)
        self.assertEqual(len(self.client.get(reverse("admin_seats") + "?status=occupied").context["page_obj"]), 0)


class AdminStudentTests(TestCase):
    def setUp(self):
        make_admin()
        self.client.login(username="boss", password=PASSWORD)

    def test_approve_reject_and_search(self):
        pending = make_student("newbie", approved=False)
        self.client.post(reverse("admin_student_action", args=[pending.pk, "approve"]))
        pending.refresh_from_db()
        self.assertTrue(pending.is_approved)
        self.assertContains(self.client.get(reverse("admin_students"), {"q": pending.student_id}), "Newbie")
        self.assertNotContains(self.client.get(reverse("admin_students"), {"q": "zzzz"}), "Newbie")
        self.assertContains(self.client.get(reverse("admin_students"), {"status": "approved"}), "Newbie")

    def test_deactivate_releases_seat_and_blocks_login(self):
        student, _ = make_member("asha")
        allocate_seat(student, make_seat("A1"))
        self.client.post(reverse("admin_student_action", args=[student.pk, "deactivate"]))
        student.user.refresh_from_db()
        self.assertFalse(student.user.is_active)
        self.assertIsNone(student.active_booking)
        self.client.logout()
        self.client.post(reverse("login"), {"username": "asha", "password": PASSWORD})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.login(username="boss", password=PASSWORD)
        self.client.post(reverse("admin_student_action", args=[student.pk, "reactivate"]))
        student.user.refresh_from_db()
        self.assertTrue(student.user.is_active)

    def test_actions_require_post_and_open_redirect_blocked(self):
        student = make_student("asha", approved=False)
        self.assertEqual(self.client.get(reverse("admin_student_action", args=[student.pk, "approve"])).status_code, 405)
        response = self.client.post(reverse("admin_student_action", args=[student.pk, "approve"]), {"next": "https://evil.example/"})
        self.assertRedirects(response, reverse("admin_student_detail", args=[student.pk]))

    def test_detail_and_plan_management(self):
        student, _ = make_member("asha")
        self.assertContains(self.client.get(reverse("admin_student_detail", args=[student.pk])), "Remaining due")
        self.client.post(reverse("admin_plan_add"), {"name": "Quarterly", "duration_days": 90, "price": "2500.00", "description": "3 months", "is_active": "on"})
        plan = MembershipPlan.objects.get(name="Quarterly")
        response = self.client.post(reverse("admin_plan_add"), {"name": "Bad", "duration_days": 0, "price": "-5"})
        self.assertTrue(response.context["form"].errors)
        self.client.post(reverse("admin_plan_edit", args=[plan.pk]), {"name": "Quarterly", "duration_days": 90, "price": "2600.00"})
        plan.refresh_from_db()
        self.assertEqual(str(plan.price), "2600.00")
        self.assertFalse(plan.is_active)
        self.client.post(reverse("admin_membership_add"), {"student": student.pk, "plan": make_plan("Zed").pk})
        self.assertEqual(student.memberships.count(), 2)

    def test_enquiries_page(self):
        from website.models import ContactEnquiry
        enquiry = ContactEnquiry.objects.create(name="V", email="v@x.com", message="hi")
        self.assertContains(self.client.get(reverse("admin_enquiries")), "hi")
        self.client.post(reverse("admin_enquiry_handled", args=[enquiry.pk]))
        enquiry.refresh_from_db()
        self.assertTrue(enquiry.is_handled)
