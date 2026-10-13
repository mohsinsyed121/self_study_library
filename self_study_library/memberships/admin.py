from django.contrib import admin

from .models import Membership, MembershipPlan

admin.site.register(MembershipPlan)
admin.site.register(Membership)
