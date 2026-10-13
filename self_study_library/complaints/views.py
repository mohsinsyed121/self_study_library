from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import approved_student_required, student_required

from .forms import ComplaintForm
from .models import Complaint


@student_required
def complaint_list(request):
    page = Paginator(request.student.complaints.all(), 10).get_page(request.GET.get("page"))
    return render(request, "complaints/complaint_list.html", {"page_obj": page})


@approved_student_required
def complaint_create(request):
    form = ComplaintForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        complaint = form.save(commit=False)
        complaint.student = request.student  # never taken from the form
        complaint.save()
        messages.success(request, "Your complaint was submitted.")
        return redirect("complaint_detail", pk=complaint.pk)
    return render(request, "complaints/complaint_create.html", {"form": form})


@student_required
def complaint_detail(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, student=request.student)  # own complaints only
    return render(request, "complaints/complaint_detail.html", {"complaint": complaint})
