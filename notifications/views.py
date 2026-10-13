from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import student_required


@student_required
def notification_list(request):
    # Only this user's notifications are ever queried.
    queryset = request.user.notifications.all()
    page = Paginator(queryset, 15).get_page(request.GET.get("page"))
    return render(request, "notifications/notification_list.html", {"page_obj": page})


@student_required
@require_POST
def mark_read(request, pk):
    note = get_object_or_404(request.user.notifications, pk=pk)  # 404 for other users' notes
    note.is_read = True
    note.save(update_fields=["is_read"])
    return redirect("notification_list")


@student_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("notification_list")
