from django import forms

from students.models import phone_validator

from .models import ContactEnquiry, SiteSettings


class ContactForm(forms.ModelForm):
    phone = forms.CharField(max_length=20, required=False, validators=[phone_validator])

    class Meta:
        model = ContactEnquiry
        fields = ["name", "email", "phone", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["library_name", "tagline", "logo", "about_text", "address", "phone", "email",
                  "opening_time", "closing_time", "rules"]
        widgets = {
            "opening_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "closing_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "about_text": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 2}),
            "rules": forms.Textarea(attrs={"rows": 6}),
        }
        help_texts = {"rules": "One rule per line."}

    def clean(self):
        cleaned = super().clean()
        opening, closing = cleaned.get("opening_time"), cleaned.get("closing_time")
        if opening and closing and closing <= opening:
            self.add_error("closing_time", "Closing time must be after opening time.")
        return cleaned
