from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.decorators import student_required

from .forms import StudentProfileForm


@student_required
def dashboard(request):
    """Student home page. Everything is read for request.student only."""
    from payments.services import fee_summary_for  # local import avoids circular imports

    student = request.student
    summary = fee_summary_for(student)
    context = {
        "student": student,
        "membership": student.current_membership,
        "booking": student.active_booking,
        "summary": summary,
        "recent_payments": student.payments_queryset()[:5],
        "notifications": request.user.notifications.all()[:5],
        "complaints": student.complaints.all()[:3],
    }
    return render(request, "students/dashboard.html", context)


@student_required
def profile(request):
    return render(request, "students/profile.html", {"student": request.student})


@student_required
def profile_edit(request):
    form = StudentProfileForm(request.POST or None, request.FILES or None, instance=request.student)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("student_profile")
    return render(request, "students/profile_edit.html", {"form": form})
