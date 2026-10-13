from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction

from students.models import StudentProfile, phone_validator

from .models import User


class StudentRegistrationForm(UserCreationForm):
    """Creates the User and the StudentProfile together."""

    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    phone = forms.CharField(max_length=15, validators=[phone_validator])
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=True)
        StudentProfile.objects.create(
            user=user,
            phone=self.cleaned_data["phone"],
            address=self.cleaned_data["address"],
        )
        return user


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Wrong username or password. Please check and try again.",
        "inactive": "This account has been deactivated. Please contact the library.",
    }
