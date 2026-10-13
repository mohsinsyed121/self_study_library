from django import forms
from django.utils import timezone

from .models import FeeRecord, Payment


class ReportPaymentForm(forms.ModelForm):
    """Student tells the library they paid. It is NOT counted until an admin verifies it."""

    class Meta:
        model = Payment
        fields = ["amount", "method", "reference", "paid_on"]
        widgets = {"paid_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, fee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fee = fee

    def clean_paid_on(self):
        paid_on = self.cleaned_data["paid_on"]
        if paid_on > timezone.localdate():
            raise forms.ValidationError("Payment date cannot be in the future.")
        return paid_on

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        if self.fee and amount > self.fee.payable_now:
            raise forms.ValidationError(f"You can pay at most ₹{self.fee.payable_now} for this fee.")
        return amount


class AdminPaymentForm(ReportPaymentForm):
    """Admin version: also picks the fee and can confirm immediately."""

    fee = forms.ModelChoiceField(queryset=FeeRecord.objects.none())
    confirm = forms.BooleanField(required=False, initial=True, label="Mark as confirmed (money received)")

    class Meta(ReportPaymentForm.Meta):
        fields = ["fee", "amount", "method", "reference", "paid_on", "confirm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fee"].queryset = FeeRecord.objects.select_related("student__user")
        self.order_fields(["fee", "amount", "method", "reference", "paid_on", "confirm"])

    def clean(self):
        cleaned = forms.ModelForm.clean(self)
        fee, amount = cleaned.get("fee"), cleaned.get("amount")
        if fee and amount:
            limit = fee.remaining_due if cleaned.get("confirm") else fee.payable_now
            if amount > limit:
                self.add_error("amount", f"Amount is more than the balance that can still be paid (₹{limit}).")
        return cleaned

    def clean_amount(self):  # the amount limit is checked in clean() once the fee is known
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount


class FeeRecordForm(forms.ModelForm):
    """Admin adds an extra fee (for example a late fee or locker fee)."""

    class Meta:
        model = FeeRecord
        fields = ["student", "description", "amount", "due_date"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = self.fields["student"].queryset.select_related("user")
