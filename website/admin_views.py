from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.utils import paginate

from .forms import SiteSettingsForm
from .models import ContactEnquiry, SiteSettings


@admin_required
def settings_view(request):
    form = SiteSettingsForm(request.POST or None, request.FILES or None, instance=SiteSettings.load())
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Website settings saved.")
        return redirect("admin_settings")
    return render(request, "admin_panel/settings.html", {"form": form})


@admin_required
def enquiry_list(request):
    return render(request, "admin_panel/enquiries.html", {"page_obj": paginate(request, ContactEnquiry.objects.all())})


@admin_required
@require_POST
def enquiry_handled(request, pk):
    enquiry = get_object_or_404(ContactEnquiry, pk=pk)
    enquiry.is_handled = True
    enquiry.save(update_fields=["is_handled"])
    return redirect("admin_enquiries")
