from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.decorators import approved_student_required, student_required

from .forms import MembershipRequestForm
from .models import Membership, MembershipPlan
from .services import MembershipError, cancel_membership, request_membership


@student_required
def plans(request):
    return render(request, "memberships/plans.html", {"plans": MembershipPlan.objects.filter(is_active=True)})


@student_required
def my_membership(request):
    student = request.student
    context = {
        "current": student.current_membership,
        "pending": student.memberships.filter(status=Membership.PENDING).first(),
        "history": student.memberships.select_related("plan"),
    }
    return render(request, "memberships/my_membership.html", context)


@approved_student_required
def renew(request):
    """Request a new plan or a renewal. The admin activates it after payment is arranged."""
    initial = {"plan": request.GET.get("plan")}
    form = MembershipRequestForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            request_membership(request.student, form.cleaned_data["plan"])
            messages.success(request, "Request sent. The library will activate your membership soon.")
            return redirect("my_membership")
        except MembershipError as error:
            messages.error(request, str(error))
    return render(request, "memberships/renew.html", {"form": form, "current": request.student.current_membership})


@student_required
def cancel_request(request, pk):
    if request.method == "POST":
        membership = request.student.memberships.filter(pk=pk).first()  # own records only
        if membership:
            try:
                cancel_membership(membership)
                messages.success(request, "Membership request cancelled.")
            except MembershipError as error:
                messages.error(request, str(error))
    return redirect("my_membership")
