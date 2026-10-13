from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import admin_required, student_required
from students.models import StudentProfile

from .forms import FindStudentForm
from .utils import qr_data_uri


@student_required
def my_id_card(request):
    student = request.student
    # The QR holds ONLY a verification link with a random token: no name, phone or payment data.
    verify_url = request.build_absolute_uri(reverse("verify_id_card", args=[student.qr_token]))
    return render(request, "id_cards/my_id_card.html", {
        "student": student,
        "membership": student.current_membership,
        "qr_image": qr_data_uri(verify_url),
    })


@admin_required
def verify_id_card(request, token):
    """Only library admins can see student details after scanning a card."""
    student = get_object_or_404(StudentProfile.objects.select_related("user"), qr_token=token)
    return render(request, "id_cards/verify_id_card.html", {
        "student": student,
        "membership": student.current_membership,
        "booking": student.active_booking,
    })


@admin_required
def find_student(request):
    """Manual lookup when a QR code cannot be scanned."""
    form = FindStudentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        student = StudentProfile.objects.filter(student_id__iexact=form.cleaned_data["student_id"].strip()).first()
        if student:
            return redirect("verify_id_card", token=student.qr_token)
        messages.error(request, "No student found with that ID.")
    return render(request, "id_cards/find_student.html", {"form": form})
