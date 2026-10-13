from decimal import Decimal

from django.contrib import messages
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.utils import paginate

from .forms import AdminPaymentForm, FeeRecordForm
from .models import FeeRecord, Payment
from .services import PaymentError, confirm_payment, record_payment, reject_payment


@admin_required
def fee_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    paid = Coalesce(Sum("payments__amount", filter=Q(payments__status="confirmed")),
                    Value(Decimal("0.00")), output_field=DecimalField())
    fees = FeeRecord.objects.select_related("student__user").annotate(paid_total=paid).order_by("-created_at", "-id")
    if query:
        fees = fees.filter(Q(student__student_id__icontains=query) | Q(student__user__first_name__icontains=query)
                           | Q(student__user__last_name__icontains=query) | Q(description__icontains=query))
    if status == "paid":
        fees = fees.filter(paid_total__gte=F("amount"))
    elif status == "unpaid":
        fees = fees.filter(paid_total=0)
    elif status == "partial":
        fees = fees.filter(paid_total__gt=0, paid_total__lt=F("amount"))
    elif status == "due":
        fees = fees.filter(paid_total__lt=F("amount"))
    return render(request, "admin_panel/fees.html", {"page_obj": paginate(request, fees), "q": query, "status": status})


@admin_required
def fee_add(request):
    form = FeeRecordForm(request.POST or None, initial={"student": request.GET.get("student")})
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fee added.")
        return redirect("admin_fees")
    return render(request, "admin_panel/payment_form.html", {"form": form, "title": "Add a fee"})


@admin_required
def payment_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    payments = Payment.objects.select_related("fee__student__user")
    if status in dict(Payment.STATUS_CHOICES):
        payments = payments.filter(status=status)
    if query:
        payments = payments.filter(Q(fee__student__student_id__icontains=query) | Q(reference__icontains=query)
                                   | Q(receipt_number__icontains=query) | Q(fee__student__user__first_name__icontains=query))
    return render(request, "admin_panel/payments.html", {
        "page_obj": paginate(request, payments), "q": query, "status": status,
        "status_choices": Payment.STATUS_CHOICES,
    })


@admin_required
def payment_add(request):
    initial = {"fee": request.GET.get("fee")}
    form = AdminPaymentForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            record_payment(data["fee"], data["amount"], data["method"], data["reference"],
                           data["paid_on"], request.user, confirm=data["confirm"])
            messages.success(request, "Payment recorded.")
            return redirect("admin_payments")
        except PaymentError as error:
            form.add_error(None, str(error))
    return render(request, "admin_panel/payment_form.html", {"form": form, "title": "Record a payment"})


@admin_required
@require_POST
def payment_action(request, pk, action):
    payment = get_object_or_404(Payment, pk=pk)
    try:
        if action == "confirm":
            confirm_payment(payment, request.user)
            messages.success(request, "Payment confirmed.")
        elif action == "reject":
            reject_payment(payment, request.user)
            messages.success(request, "Payment rejected.")
        else:
            messages.error(request, "Unknown action.")
    except PaymentError as error:
        messages.error(request, str(error))
    return redirect("admin_payments")
