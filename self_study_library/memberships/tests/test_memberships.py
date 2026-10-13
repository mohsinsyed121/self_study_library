from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from config.test_helpers import PASSWORD, make_admin, make_member, make_plan, make_seat, make_student
from memberships.models import Membership
from memberships.services import (MembershipError, activate_membership, expire_overdue_memberships,
                                  request_membership)
from payments.models import FeeRecord
from seats.services import allocate_seat


class MembershipTests(TestCase):
    def setUp(self):
        self.plan = make_plan("Monthly", 30, "1200.00")
        self.student = make_student("asha")
        self.today = timezone.localdate()

    def test_activation_sets_dates_and_creates_fee(self):
        membership = request_membership(self.student, self.plan)
        self.assertEqual(membership.status, "pending")
        self.assertIsNone(membership.start_date)
        activate_membership(membership)
        membership.refresh_from_db()
        self.assertEqual(membership.status, "active")
        self.assertEqual(membership.start_date, self.today)
        self.assertEqual(membership.end_date, self.today + timedelta(days=29))
        fee = FeeRecord.objects.get(membership=membership)
        self.assertEqual(str(fee.amount), "1200.00")
        self.assertTrue(self.student.user.notifications.filter(title="Membership activated").exists())

    def test_renewal_starts_after_current_ends_and_keeps_history(self):
        first = activate_membership(request_membership(self.student, self.plan))
        second = activate_membership(request_membership(self.student, self.plan))
        self.assertEqual(second.start_date, first.end_date + timedelta(days=1))
        self.assertEqual(Membership.objects.filter(student=self.student).count(), 2)  # history kept
        self.assertEqual(FeeRecord.objects.filter(student=self.student).count(), 2)

    def test_price_is_a_snapshot(self):
        membership = request_membership(self.student, self.plan)
        self.plan.price = 9999
        self.plan.save()
        activate_membership(membership)
        self.assertEqual(str(FeeRecord.objects.get().amount), "1200.00")

    def test_only_one_pending_request(self):
        request_membership(self.student, self.plan)
        with self.assertRaises(MembershipError):
            request_membership(self.student, self.plan)

    def test_inactive_plan_and_unapproved_student(self):
        self.plan.is_active = False
        self.plan.save()
        with self.assertRaises(MembershipError):
            request_membership(self.student, self.plan)
        with self.assertRaises(MembershipError):
            request_membership(make_student("pend", approved=False), make_plan("Other"))

    def test_cannot_activate_twice(self):
        membership = activate_membership(request_membership(self.student, self.plan))
        with self.assertRaises(MembershipError):
            activate_membership(membership)

    def test_expiry_marks_expired_and_releases_seat(self):
        membership = activate_membership(request_membership(self.student, self.plan))
        booking = allocate_seat(self.student, make_seat("A1"))
        count = expire_overdue_memberships(today=membership.end_date + timedelta(days=1))
        self.assertEqual(count, 1)
        membership.refresh_from_db(); booking.refresh_from_db()
        self.assertEqual(membership.status, "expired")
        self.assertEqual(booking.status, "ended")
        self.assertIsNone(self.student.current_membership)
        self.assertTrue(self.student.user.notifications.filter(title="Membership expired").exists())

    def test_not_expired_before_end_date(self):
        membership = activate_membership(request_membership(self.student, self.plan))
        self.assertEqual(expire_overdue_memberships(today=membership.end_date), 0)

    def test_renewed_student_keeps_seat_when_first_period_ends(self):
        first = activate_membership(request_membership(self.student, self.plan))
        activate_membership(request_membership(self.student, self.plan))
        booking = allocate_seat(self.student, make_seat("A1"))
        expire_overdue_memberships(today=first.end_date + timedelta(days=1))
        booking.refresh_from_db()
        self.assertEqual(booking.status, "allocated")


class MembershipViewTests(TestCase):
    def test_student_requests_and_admin_activates(self):
        plan = make_plan("Monthly")
        student = make_student("asha")
        make_admin()
        self.client.login(username="asha", password=PASSWORD)
        self.client.post(reverse("renew_membership"), {"plan": plan.pk})
        membership = Membership.objects.get()
        self.assertEqual(membership.status, "pending")
        self.client.logout()
        self.client.login(username="boss", password=PASSWORD)
        self.client.post(reverse("admin_membership_action", args=[membership.pk, "activate"]))
        membership.refresh_from_db()
        self.assertEqual(membership.status, "active")

    def test_expire_command_runs(self):
        from django.core.management import call_command
        call_command("expire_memberships")
