from django.contrib import admin

from .models import ContactEnquiry, SiteSettings

admin.site.register(SiteSettings)
admin.site.register(ContactEnquiry)
