from django.contrib import messages
from django.shortcuts import redirect, render

from memberships.models import MembershipPlan
from seats.services import seat_counts

from .forms import ContactForm


def _active_plans():
    return MembershipPlan.objects.filter(is_active=True)


def home(request):
    context = {"plans": _active_plans()[:3], "counts": seat_counts()}
    return render(request, "website/home.html", context)


def about(request):
    return render(request, "website/about.html")


def facilities(request):
    return render(request, "website/facilities.html")


def gallery(request):
    # Placeholder tiles. See the comment inside website/gallery.html to use real photos.
    tiles = ["Study hall", "Reading desks", "Entrance", "Water corner", "Charging desks", "Quiet zone"]
    return render(request, "website/gallery.html", {"tiles": tiles})


def membership_plans(request):
    return render(request, "website/membership_plans.html", {"plans": _active_plans()})


def rules(request):
    return render(request, "website/rules.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thank you! We received your message and will get back to you.")
        return redirect("contact")
    return render(request, "website/contact.html", {"form": form})


# ----- custom error pages -----
def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)
