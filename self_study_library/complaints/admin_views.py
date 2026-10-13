from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required
from accounts.utils import paginate
from notifications.services import notify

from .forms import ComplaintResponseForm
from .models import Complaint


@admin_required
def complaint_list(request):
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    complaints = Complaint.objects.select_related("student__user")
    if status in dict(Complaint.STATUS_CHOICES):
        complaints = complaints.filter(status=status)
    if query:
        complaints = complaints.filter(Q(subject__icontains=query) | Q(student__student_id__icontains=query)
                                       | Q(student__user__first_name__icontains=query))
    return render(request, "admin_panel/complaints.html", {
        "page_obj": paginate(request, complaints), "status": status, "q": query,
        "status_choices": Complaint.STATUS_CHOICES,
    })


@admin_required
def complaint_detail(request, pk):
    complaint = get_object_or_404(Complaint.objects.select_related("student__user"), pk=pk)
    old_status, old_response = complaint.status, complaint.admin_response
    form = ComplaintResponseForm(request.POST or None, instance=complaint)
    if request.method == "POST" and form.is_valid():
        form.save()
        if complaint.status != old_status or complaint.admin_response != old_response:
            notify(complaint.student.user, "Complaint update",
                   f'Your complaint "{complaint.subject}" is now {complaint.get_status_display()}.')
        messages.success(request, "Complaint updated and the student was notified.")
        return redirect("admin_complaints")
    return render(request, "admin_panel/complaint_detail.html", {"complaint": complaint, "form": form})
