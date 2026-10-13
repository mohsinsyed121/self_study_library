from django import forms

from students.models import StudentProfile

from .models import MembershipPlan


class MembershipPlanForm(forms.ModelForm):
    class Meta:
        model = MembershipPlan
        fields = ["name", "duration_days", "price", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class MembershipRequestForm(forms.Form):
    plan = forms.ModelChoiceField(queryset=MembershipPlan.objects.filter(is_active=True), empty_label="Choose a plan")


class AdminMembershipForm(forms.Form):
    """Admin creates + activates a membership for a student."""

    student = forms.ModelChoiceField(queryset=StudentProfile.objects.none())
    plan = forms.ModelChoiceField(queryset=MembershipPlan.objects.filter(is_active=True))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = StudentProfile.objects.filter(approval_status="approved").select_related("user")
