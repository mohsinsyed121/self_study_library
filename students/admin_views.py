from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.utils import paginate

from .models import StudentProfile


@admin_required
def student_list(request):
    students = StudentProfile.objects.select_related("user")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        students = students.filter(
            Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query)
            | Q(user__username__icontains=query) | Q(user__email__icontains=query)
            | Q(student_id__icontains=query) | Q(phone__icontains=query)
        )
    if status == "deactivated":
        students = students.filter(user__is_active=False)
    elif status in ("pending", "approved", "rejected"):
        students = students.filter(approval_status=status, user__is_active=True)
    return render(request, "admin_panel/students.html", {
        "page_obj": paginate(request, students), "q": query, "status": status,
    })


@admin_required
def student_detail(request, pk):
    student = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)
    from payments.services import fee_summary_for

    return render(request, "admin_panel/student_detail.html", {
        "student": student,
        "memberships": student.memberships.select_related("plan"),
        "bookings": student.bookings.select_related("seat")[:10],
        "fees": student.fees.all(),
        "summary": fee_summary_for(student),
    })


@admin_required
@require_POST
def student_action(request, pk, action):
    """Approve / reject / deactivate / reactivate. POST only, admin only."""
    student = get_object_or_404(StudentProfile, pk=pk)
    if action == "approve":
        student.approve()
        messages.success(request, f"{student.full_name} approved.")
    elif action == "reject":
        student.reject()
        messages.success(request, f"{student.full_name} rejected.")
    elif action == "deactivate":
        from seats.models import SeatBooking
        from seats.services import cancel_booking

        for booking in student.bookings.filter(status__in=SeatBooking.ACTIVE_STATUSES):
            cancel_booking(booking, by_admin=True)  # free the seat
        student.deactivate()
        messages.success(request, f"{student.full_name} deactivated. Their seat (if any) was released.")
    elif action == "reactivate":
        student.reactivate()
        messages.success(request, f"{student.full_name} reactivated.")
    else:
        messages.error(request, "Unknown action.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("admin_student_detail", pk=pk)
