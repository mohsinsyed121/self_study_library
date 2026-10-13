"""All dashboard and report numbers are calculated from real database rows."""
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from complaints.models import Complaint
from memberships.models import Membership
from payments.models import FeeRecord, Payment
from seats.services import seat_counts
from students.models import StudentProfile

ZERO = Decimal("0.00")


def _sum(queryset, field="amount"):
    return queryset.aggregate(t=Sum(field))["t"] or ZERO


def total_fees():
    return _sum(FeeRecord.objects.all())


def confirmed_total():
    return _sum(Payment.objects.filter(status=Payment.CONFIRMED))


def pending_fees():
    """Money still owed: total fees - confirmed payments."""
    return total_fees() - confirmed_total()


def dashboard_stats():
    today = timezone.localdate()
    seats = seat_counts()
    month_start = today.replace(day=1)
    return {
        "total_students": StudentProfile.objects.count(),
        "pending_approvals": StudentProfile.objects.filter(approval_status="pending").count(),
        "active_memberships": Membership.objects.filter(status="active", start_date__lte=today, end_date__gte=today).count(),
        "seats": seats,
        "pending_fees": pending_fees(),
        "confirmed_collection": confirmed_total(),
        "month_collection": _sum(Payment.objects.filter(status=Payment.CONFIRMED, paid_on__gte=month_start)),
        "payments_to_verify": Payment.objects.filter(status=Payment.PENDING).count(),
        "pending_complaints": Complaint.objects.filter(status=Complaint.PENDING).count(),
        "recent_students": StudentProfile.objects.select_related("user")[:5],
        "recent_payments": Payment.objects.select_related("fee__student__user")[:5],
        "recent_complaints": Complaint.objects.filter(status=Complaint.PENDING).select_related("student__user")[:5],
    }


def date_range_report(start, end):
    """Totals between two dates (inclusive). Collections and dues are kept separate."""
    confirmed = Payment.objects.filter(status=Payment.CONFIRMED, paid_on__range=(start, end))
    by_method = (confirmed.values("method").annotate(total=Sum("amount"), count=Count("id")).order_by("-total"))
    method_names = dict(Payment.METHOD_CHOICES)
    methods = [{"name": method_names.get(row["method"], row["method"]), "total": row["total"], "count": row["count"]} for row in by_method]
    fees_in_range = FeeRecord.objects.filter(created_at__date__range=(start, end))
    # Two separate queries (one for fees, one for confirmed payments) so that joining
    # the tables can never count a fee twice.
    fee_totals = dict(FeeRecord.objects.values_list("student").annotate(t=Sum("amount")))
    paid_totals = dict(
        Payment.objects.filter(status=Payment.CONFIRMED).values_list("fee__student").annotate(t=Sum("amount"))
    )
    owing = []
    students = StudentProfile.objects.select_related("user").in_bulk(list(fee_totals))
    for student_id, fee_total in fee_totals.items():
        due = fee_total - paid_totals.get(student_id, ZERO)
        if due > 0:
            owing.append({"student": students[student_id], "due": due})
    owing.sort(key=lambda row: row["due"], reverse=True)
    return {
        "new_students": StudentProfile.objects.filter(created_at__date__range=(start, end)).count(),
        "memberships_activated": Membership.objects.filter(start_date__range=(start, end), status__in=["active", "expired"]).count(),
        "confirmed_collection": _sum(confirmed),
        "pending_payments": _sum(Payment.objects.filter(status=Payment.PENDING, paid_on__range=(start, end))),
        "fees_generated": _sum(fees_in_range),
        "outstanding_dues": pending_fees(),  # all-time, not only this range
        "methods": methods,
        "owing": owing[:20],
        "complaints_received": Complaint.objects.filter(created_at__date__range=(start, end)).count(),
        "complaints_resolved": Complaint.objects.filter(status=Complaint.RESOLVED, updated_at__date__range=(start, end)).count(),
    }
