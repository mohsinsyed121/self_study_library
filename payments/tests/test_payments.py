from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from config.test_helpers import PASSWORD, make_admin, make_member, make_plan, make_student
from payments.forms import AdminPaymentForm, ReportPaymentForm
from payments.models import Payment
from payments.services import (PaymentError, confirm_payment, fee_summary_for, record_payment,
                               reject_payment, submit_payment)

import datetime


class FeeCalculationTests(TestCase):
    def setUp(self):
        self.student, self.membership = make_member("asha", make_plan("M", 30, "1000.00"))
        self.fee = self.membership.fee
        self.admin = make_admin()
        self.today = datetime.date.today()

    def test_new_fee_is_fully_due(self):
        summary = fee_summary_for(self.student)
        self.assertEqual(summary["total_fee"], Decimal("1000.00"))
        self.assertEqual(summary["remaining_due"], Decimal("1000.00"))
        self.assertEqual(self.fee.payment_status, "Unpaid")

    def test_partial_payments_reduce_due(self):
        record_payment(self.fee, Decimal("400.00"), "cash", "", self.today, self.admin)
        self.assertEqual(self.fee.remaining_due, Decimal("600.00"))
        self.assertEqual(self.fee.payment_status, "Partial")
        record_payment(self.fee, Decimal("600.00"), "upi", "UPI123", self.today, self.admin)
        self.assertEqual(self.fee.remaining_due, Decimal("0.00"))
        self.assertEqual(self.fee.payment_status, "Paid")
        self.assertEqual(fee_summary_for(self.student)["total_paid"], Decimal("1000.00"))

    def test_pending_and_rejected_payments_do_not_count(self):
        payment = submit_payment(self.fee, Decimal("300.00"), "upi", "X1", self.today, self.student.user)
        summary = fee_summary_for(self.student)
        self.assertEqual(summary["remaining_due"], Decimal("1000.00"))   # still fully due
        self.assertEqual(summary["pending_verification"], Decimal("300.00"))
        reject_payment(payment, self.admin)
        self.assertEqual(fee_summary_for(self.student)["pending_verification"], Decimal("0.00"))
        self.assertEqual(self.fee.remaining_due, Decimal("1000.00"))

    def test_verification_confirms_and_creates_receipt(self):
        payment = submit_payment(self.fee, Decimal("250.00"), "cash", "", self.today, self.student.user)
        confirm_payment(payment, self.admin)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "confirmed")
        self.assertTrue(payment.receipt_number.startswith("RCP"))
        self.assertEqual(payment.verified_by, self.admin)
        self.assertEqual(self.fee.remaining_due, Decimal("750.00"))
        self.assertTrue(self.student.user.notifications.filter(title="Payment confirmed").exists())

    def test_cannot_confirm_twice(self):
        payment = record_payment(self.fee, Decimal("100.00"), "cash", "", self.today, self.admin)
        with self.assertRaises(PaymentError):
            confirm_payment(payment, self.admin)

    def test_overpayment_blocked(self):
        with self.assertRaises(PaymentError):
            record_payment(self.fee, Decimal("1000.01"), "cash", "", self.today, self.admin)
        record_payment(self.fee, Decimal("900.00"), "cash", "", self.today, self.admin)
        with self.assertRaises(PaymentError):
            record_payment(self.fee, Decimal("100.01"), "cash", "", self.today, self.admin)
        self.assertEqual(Payment.objects.count(), 1)

    def test_zero_and_negative_payments_blocked(self):
        for bad in (Decimal("0"), Decimal("-5.00")):
            with self.assertRaises(PaymentError):
                record_payment(self.fee, bad, "cash", "", self.today, self.admin)

    def test_pending_payments_cannot_exceed_balance_together(self):
        submit_payment(self.fee, Decimal("800.00"), "upi", "A", self.today, self.student.user)
        with self.assertRaises(PaymentError):
            submit_payment(self.fee, Decimal("300.00"), "upi", "B", self.today, self.student.user)

    def test_confirm_rechecks_overpayment(self):
        p1 = submit_payment(self.fee, Decimal("600.00"), "upi", "A", self.today, self.student.user)
        record_payment(self.fee, Decimal("500.00"), "cash", "", self.today, self.admin)  # confirmed meanwhile
        with self.assertRaises(PaymentError):
            confirm_payment(p1, self.admin)

    def test_money_uses_decimal_without_rounding_errors(self):
        for _ in range(3):
            record_payment(self.fee, Decimal("0.10"), "cash", "", self.today, self.admin)
        self.assertEqual(self.fee.remaining_due, Decimal("999.70"))


class PaymentFormTests(TestCase):
    def setUp(self):
        self.student, self.membership = make_member("asha", make_plan("M", 30, "500.00"))
        self.fee = self.membership.fee

    def test_student_form_validation(self):
        base = {"method": "cash", "reference": "", "paid_on": datetime.date.today()}
        self.assertTrue(ReportPaymentForm(dict(base, amount="100"), fee=self.fee).is_valid())
        self.assertFalse(ReportPaymentForm(dict(base, amount="-1"), fee=self.fee).is_valid())
        self.assertFalse(ReportPaymentForm(dict(base, amount="501"), fee=self.fee).is_valid())
        future = datetime.date.today() + datetime.timedelta(days=2)
        self.assertFalse(ReportPaymentForm(dict(base, amount="100", paid_on=future), fee=self.fee).is_valid())

    def test_admin_form_blocks_overpayment(self):
        data = {"fee": self.fee.pk, "amount": "600", "method": "cash", "reference": "", "paid_on": datetime.date.today(), "confirm": "on"}
        form = AdminPaymentForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)


class PaymentViewTests(TestCase):
    def setUp(self):
        self.asha, self.membership = make_member("asha", make_plan("M", 30, "500.00"))
        self.ravi, self.ravi_membership = make_member("ravi", make_plan("R", 30, "700.00"))
        make_admin()

    def test_student_reports_payment_and_admin_verifies(self):
        self.client.login(username="asha", password=PASSWORD)
        response = self.client.post(reverse("report_payment", args=[self.membership.fee.pk]),
                                    {"amount": "200", "method": "upi", "reference": "UPI9", "paid_on": datetime.date.today()})
        self.assertRedirects(response, reverse("payment_history"))
        payment = Payment.objects.get()
        self.assertEqual(payment.status, "pending")
        self.assertEqual(self.membership.fee.remaining_due, Decimal("500.00"))
        self.client.logout()
        self.client.login(username="boss", password=PASSWORD)
        self.client.post(reverse("admin_payment_action", args=[payment.pk, "confirm"]))
        payment.refresh_from_db()
        self.assertEqual(payment.status, "confirmed")
        self.assertEqual(self.membership.fee.remaining_due, Decimal("300.00"))

    def test_student_cannot_verify_own_payment(self):
        payment = Payment.objects.create(fee=self.membership.fee, amount=100, method="cash", status="pending")
        self.client.login(username="asha", password=PASSWORD)
        self.assertEqual(self.client.post(reverse("admin_payment_action", args=[payment.pk, "confirm"])).status_code, 403)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")

    def test_receipt_only_for_confirmed_and_own_payments(self):
        admin = make_admin("boss2")
        mine = record_payment(self.membership.fee, Decimal("100"), "cash", "", datetime.date.today(), admin)
        pending = Payment.objects.create(fee=self.membership.fee, amount=50, method="cash", status="pending")
        theirs = record_payment(self.ravi_membership.fee, Decimal("100"), "cash", "", datetime.date.today(), admin)
        self.client.login(username="asha", password=PASSWORD)
        self.assertContains(self.client.get(reverse("payment_receipt", args=[mine.pk])), mine.receipt_number)
        self.assertEqual(self.client.get(reverse("payment_receipt", args=[pending.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("payment_receipt", args=[theirs.pk])).status_code, 404)

    def test_admin_fee_and_payment_pages(self):
        self.client.login(username="boss", password=PASSWORD)
        for name in ("admin_fees", "admin_payments", "admin_fee_add", "admin_payment_add"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertContains(self.client.get(reverse("admin_fees") + "?status=unpaid"), "asha".title())
