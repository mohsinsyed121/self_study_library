from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from notifications.services import notify

from .forms import LoginForm, StudentRegistrationForm


@never_cache
def register(request):
    if request.user.is_authenticated:
        return redirect("after_login")
    form = StudentRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        notify(user, "Welcome!", "Your registration was received. The library will approve it shortly.")
        login(request, user)
        messages.success(request, "Registration successful. Your account is waiting for admin approval.")
        return redirect("student_dashboard")
    return render(request, "accounts/register.html", {"form": form})


class StudentLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        # Staff go to the admin panel, students to their dashboard.
        return "/manage/" if self.request.user.is_staff else "/student/"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


@never_cache
def after_login(request):
    """Landing URL used by LOGIN_REDIRECT_URL."""
    if not request.user.is_authenticated:
        return redirect("login")
    return redirect("admin_dashboard" if request.user.is_staff else "student_dashboard")


@never_cache
def logout_view(request):
    """GET shows a confirmation page; POST ends the session with Django's logout()."""
    if request.method == "POST":
        logout(request)  # clears the session completely
        messages.success(request, "You have been logged out.")
        return redirect("home")
    if not request.user.is_authenticated:
        return redirect("home")
    return render(request, "accounts/logout.html")
