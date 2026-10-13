"""Main URL configuration. Each app owns its own urls.py; admin-panel URLs live in <app>/admin_urls.py."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),  # Django's built-in admin (superuser tools)
    path("", include("website.urls")),
    path("accounts/", include("accounts.urls")),
    path("student/", include("students.urls")),
    path("seats/", include("seats.urls")),
    path("membership/", include("memberships.urls")),
    path("payments/", include("payments.urls")),
    path("id-card/", include("id_cards.urls")),
    path("complaints/", include("complaints.urls")),
    path("notifications/", include("notifications.urls")),
    # Library admin panel (staff only)
    path("manage/", include("reports.admin_urls")),
    path("manage/students/", include("students.admin_urls")),
    path("manage/seats/", include("seats.admin_urls")),
    path("manage/memberships/", include("memberships.admin_urls")),
    path("manage/payments/", include("payments.admin_urls")),
    path("manage/complaints/", include("complaints.admin_urls")),
    path("manage/", include("website.admin_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "website.views.error_403"
handler404 = "website.views.error_404"
handler500 = "website.views.error_500"
