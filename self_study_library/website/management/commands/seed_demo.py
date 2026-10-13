from decimal import Decimal

from django.core.management.base import BaseCommand

from memberships.models import MembershipPlan
from seats.models import Seat
from website.models import SiteSettings


class Command(BaseCommand):
    help = "Create starter data: website settings, 3 membership plans and 30 seats. Safe to run twice."

    def handle(self, *args, **options):
        SiteSettings.load()
        plans = [("Monthly", 30, "800.00", "One month of study access."),
                 ("Quarterly", 90, "2200.00", "Three months, save a little."),
                 ("Half-yearly", 180, "4000.00", "Six months for long preparations.")]
        for name, days, price, text in plans:
            MembershipPlan.objects.get_or_create(name=name, defaults={"duration_days": days, "price": Decimal(price), "description": text})
        for number in range(1, 31):
            Seat.objects.get_or_create(number=f"A{number}", defaults={"section": "Main hall" if number <= 20 else "Quiet zone"})
        self.stdout.write(self.style.SUCCESS("Demo data ready: settings, 3 plans, 30 seats."))
