from django import forms

from accounts.models import User

from .models import StudentProfile

MAX_PHOTO_MB = 2


class StudentProfileForm(forms.ModelForm):
    """Fields a student may edit. Student ID, QR token and approval status are NOT here."""

    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    email = forms.EmailField()

    class Meta:
        model = StudentProfile
        fields = ["phone", "address", "date_of_birth", "guardian_name", "guardian_phone", "photo"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    field_order = ["first_name", "last_name", "email", "phone", "address", "date_of_birth",
                   "guardian_name", "guardian_phone", "photo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "size") and photo.size > MAX_PHOTO_MB * 1024 * 1024:
            raise forms.ValidationError(f"Photo must be smaller than {MAX_PHOTO_MB} MB.")
        return photo

    def save(self, commit=True):
        profile = super().save(commit=commit)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.save(update_fields=["first_name", "last_name", "email"])
        return profile
