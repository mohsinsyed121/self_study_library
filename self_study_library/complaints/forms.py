from django import forms

from .models import Complaint


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["subject", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if len(text) < 10:
            raise forms.ValidationError("Please describe the problem in at least 10 characters.")
        return text


class ComplaintResponseForm(forms.ModelForm):
    """Admin: change status and write a reply."""

    class Meta:
        model = Complaint
        fields = ["status", "admin_response"]
        widgets = {"admin_response": forms.Textarea(attrs={"rows": 4})}
