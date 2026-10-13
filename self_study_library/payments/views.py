from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import approved_student_required, student_required

from .forms import ReportPaymentForm
from .models import FeeRecord, Payment
from .services import PaymentError, fee_summary_for, submit_payment


@student_required
def fee_summary(request):
    fees = request.student.fees.select_related("membership")
    return render(request, "payments/fee_summary.html", {"fees": fees, "summary": fee_summary_for(request.student)})


@student_required
def payment_history(request):
    page = Paginator(request.student.payments_queryset(), 10).get_page(request.GET.get("page"))
    return render(request, "payments/payment_history.html", {"page_obj": page})


@student_required
def payment_detail(request, pk):
    payment = get_object_or_404(Payment, pk=pk, fee__student=request.student)  # own payments only
    return render(request, "payments/payment_detail.html", {"payment": payment})


@student_required
def receipt(request, pk):
    payment = get_object_or_404(Payment, pk=pk, fee__student=request.student, status=Payment.CONFIRMED)
    return render(request, "payments/receipt.html", {"payment": payment})


@approved_student_required
def report_payment(request, fee_pk):
    """Student reports a manual payment (cash/UPI). An admin must verify it."""
    fee = get_object_or_404(FeeRecord, pk=fee_pk, student=request.student)
    form = ReportPaymentForm(request.POST or None, fee=fee)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            submit_payment(fee, data["amount"], data["method"], data["reference"], data["paid_on"], request.user)
            messages.success(request, "Payment reported. It will count after the library verifies it.")
            return redirect("payment_history")
        except PaymentError as error:
            messages.error(request, str(error))
    return render(request, "payments/report_payment.html", {"form": form, "fee": fee})
