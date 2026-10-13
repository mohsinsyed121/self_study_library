import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from complaints.models import Complaint
from config.test_helpers import PASSWORD, make_admin, make_member, make_plan, make_seat, make_student
from payments.services import record_payment, submit_payment
from reports.services import dashboard_stats, date_range_report
from seats.services import allocate_seat, request_seat


class ReportCalculationTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.today = timezone.localdate()
        self.asha, self.m1 = make_member("asha", make_plan("A", 30, "1000.00"))
        self.ravi, self.m2 = make_member("ravi", make_plan("B", 30, "2000.00"))
        make_student("pending_s", approved=False)
        record_payment(self.m1.fee, Decimal("400.00"), "cash", "", self.today, self.admin)
        record_payment(self.m2.fee, Decimal("2000.00"), "upi", "U1", self.today, self.admin)
        submit_payment(self.m1.fee, Decimal("100.00"), "upi", "U2", self.today, self.asha.user)  # pending: not counted
        allocate_seat(self.asha, make_seat("A1"))
        request_seat(self.ravi, make_seat("A2"))
        make_seat("A3")
        Complaint.objects.create(student=self.asha, subject="x", description="long enough text")

    def test_dashboard_numbers_come_from_database(self):
        stats = dashboard_stats()
        self.assertEqual(stats["total_students"], 3)
        self.assertEqual(stats["pending_approvals"], 1)
        self.assertEqual(stats["active_memberships"], 2)
        self.assertEqual(stats["confirmed_collection"], Decimal("2400.00"))
        self.assertEqual(stats["pending_fees"], Decimal("600.00"))      # 3000 fees - 2400 confirmed
        self.assertEqual(stats["payments_to_verify"], 1)
        self.assertEqual(stats["pending_complaints"], 1)
        self.assertEqual(stats["seats"], {"total": 3, "occupied": 1, "reserved": 1, "available": 1, "inactive": 0})

    def test_collections_and_dues_are_separate(self):
        report = date_range_report(self.today, self.today)
        self.assertEqual(report["confirmed_collection"], Decimal("2400.00"))
        self.assertEqual(report["pending_payments"], Decimal("100.00"))
        self.assertEqual(report["outstanding_dues"], Decimal("600.00"))
        self.assertEqual(report["fees_generated"], Decimal("3000.00"))
        self.assertEqual(report["new_students"], 3)
        methods = {row["name"]: row["total"] for row in report["methods"]}
        self.assertEqual(methods, {"Cash": Decimal("400.00"), "UPI": Decimal("2000.00")})
        self.assertEqual([row["student"] for row in report["owing"]], [self.asha])
        self.assertEqual(report["owing"][0]["due"], Decimal("600.00"))

    def test_date_range_excludes_other_days(self):
        yesterday = self.today - datetime.timedelta(days=1)
        report = date_range_report(yesterday - datetime.timedelta(days=5), yesterday)
        self.assertEqual(report["confirmed_collection"], Decimal("0.00"))
        self.assertEqual(report["new_students"], 0)

    def test_dashboard_and_report_pages(self):
        self.client.login(username="boss", password=PASSWORD)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertContains(response, "₹2,400.00")
        self.assertContains(response, "₹600.00")
        response = self.client.get(reverse("admin_reports"), {"start": self.today, "end": self.today})
        self.assertContains(response, "₹2,400.00")

    def test_invalid_date_range_shows_error(self):
        self.client.login(username="boss", password=PASSWORD)
        response = self.client.get(reverse("admin_reports"), {"start": "2026-02-01", "end": "2026-01-01"})
        self.assertContains(response, "End date must be on or after")
        self.assertIsNone(response.context["report"])
