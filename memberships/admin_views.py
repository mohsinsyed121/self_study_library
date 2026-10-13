from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.utils import paginate

from .forms import AdminMembershipForm, MembershipPlanForm
from .models import Membership, MembershipPlan
from .services import (MembershipError, activate_membership, cancel_membership,
                       create_and_activate, expire_overdue_memberships)


@admin_required
def plan_list(request):
    return render(request, "admin_panel/membership_plans.html", {"plans": MembershipPlan.objects.all()})


@admin_required
def plan_add(request):
    form = MembershipPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Plan created.")
        return redirect("admin_plans")
    return render(request, "admin_panel/plan_form.html", {"form": form, "title": "Add plan"})


@admin_required
def plan_edit(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)
    form = MembershipPlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Plan updated. Existing memberships keep their original price.")
        return redirect("admin_plans")
    return render(request, "admin_panel/plan_form.html", {"form": form, "title": f"Edit {plan.name}"})


@admin_required
def membership_list(request):
    expire_overdue_memberships()  # keep statuses fresh
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    memberships = Membership.objects.select_related("student__user", "plan")
    if status in dict(Membership.STATUS_CHOICES):
        memberships = memberships.filter(status=status)
    if query:
        memberships = memberships.filter(
            Q(student__student_id__icontains=query) | Q(student__user__first_name__icontains=query)
            | Q(student__user__last_name__icontains=query) | Q(plan__name__icontains=query))
    return render(request, "admin_panel/memberships.html", {
        "page_obj": paginate(request, memberships), "status": status, "q": query,
        "status_choices": Membership.STATUS_CHOICES,
    })


@admin_required
def membership_add(request):
    form = AdminMembershipForm(request.POST or None, initial={"student": request.GET.get("student")})
    if request.method == "POST" and form.is_valid():
        try:
            create_and_activate(form.cleaned_data["student"], form.cleaned_data["plan"])
            messages.success(request, "Membership activated and fee created.")
            return redirect("admin_memberships")
        except MembershipError as error:
            form.add_error(None, str(error))
    return render(request, "admin_panel/plan_form.html", {"form": form, "title": "Activate / renew a membership"})


@admin_required
@require_POST
def membership_action(request, pk, action):
    membership = get_object_or_404(Membership, pk=pk)
    try:
        if action == "activate":
            activate_membership(membership)
            messages.success(request, "Membership activated and fee created.")
        elif action == "cancel":
            cancel_membership(membership)
            messages.success(request, "Request cancelled.")
        else:
            messages.error(request, "Unknown action.")
    except MembershipError as error:
        messages.error(request, str(error))
    return redirect("admin_memberships")
