"""Permission decorators used by every private view.

Each decorator:
  * requires login (@login_required behaviour),
  * adds never_cache so the browser never shows an old private page from its cache
    (for example by pressing the Back button after logout),
  * checks the user's role on the SERVER (hiding a button in HTML is not security).
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache


def student_required(view_func):
    """Logged-in student with a profile. Staff users are sent to the admin panel."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return redirect("admin_dashboard")
        profile = getattr(request.user, "studentprofile", None)
        if profile is None:
            raise PermissionDenied
        request.student = profile  # views use request.student, never a URL id
        return view_func(request, *args, **kwargs)

    return never_cache(login_required(wrapper))


def approved_student_required(view_func):
    """Student whose registration has been approved by the admin."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.student.is_approved:
            messages.warning(request, "This feature is available after the library approves your registration.")
            return redirect("student_dashboard")
        return view_func(request, *args, **kwargs)

    return student_required(wrapper)


def admin_required(view_func):
    """Library admin only (is_staff). Anyone else gets the 403 page."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return never_cache(login_required(wrapper))
