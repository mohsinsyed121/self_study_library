from django import forms

from students.models import StudentProfile

from .models import Seat


class SeatForm(forms.ModelForm):
    class Meta:
        model = Seat
        fields = ["number", "section", "is_active"]

    def clean_number(self):
        return self.cleaned_data["number"].strip().upper()

    def clean_is_active(self):
        is_active = self.cleaned_data["is_active"]
        # A seat that someone is using cannot be switched off until they are moved.
        if not is_active and self.instance.pk and self.instance.current_booking:
            raise forms.ValidationError("This seat has an active booking. Cancel or move the booking first.")
        return is_active


class BulkSeatForm(forms.Form):
    """Create many seats at once, e.g. prefix 'A', 1 to 20 -> A1 ... A20."""

    prefix = forms.CharField(max_length=5, required=False, help_text="Optional letter(s) before the number, e.g. A")
    start = forms.IntegerField(min_value=1)
    end = forms.IntegerField(min_value=1)
    section = forms.CharField(max_length=50, required=False)

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start"), cleaned.get("end")
        if start and end:
            if end < start:
                self.add_error("end", "End number must be the same as or bigger than the start number.")
            elif end - start >= 200:
                self.add_error("end", "Please create at most 200 seats at a time.")
        return cleaned


class AllocateSeatForm(forms.Form):
    student = forms.ModelChoiceField(queryset=StudentProfile.objects.none())
    seat = forms.ModelChoiceField(queryset=Seat.objects.none())
    note = forms.CharField(max_length=200, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = StudentProfile.objects.filter(
            approval_status="approved", user__is_active=True
        ).select_related("user")
        self.fields["seat"].queryset = Seat.objects.filter(is_active=True)


class ReassignSeatForm(forms.Form):
    new_seat = forms.ModelChoiceField(queryset=Seat.objects.filter(is_active=True))
