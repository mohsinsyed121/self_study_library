from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import admin_required
from memberships.services import expire_overdue_memberships

from .forms import DateRangeForm
from .services import dashboard_stats, date_range_report


@admin_required
def dashboard(request):
    expire_overdue_memberships()  # refresh expired memberships before showing numbers
    return render(request, "admin_panel/dashboard.html", {"stats": dashboard_stats()})


@admin_required
def reports(request):
    today = timezone.localdate()
    data = request.GET if "start" in request.GET else {"start": today - timedelta(days=29), "end": today}
    form = DateRangeForm(data)
    report = date_range_report(form.cleaned_data["start"], form.cleaned_data["end"]) if form.is_valid() else None
    return render(request, "admin_panel/reports.html", {"form": form, "report": report})
