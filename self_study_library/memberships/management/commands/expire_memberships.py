from django.core.management.base import BaseCommand

from memberships.services import expire_overdue_memberships


class Command(BaseCommand):
    help = "Expire memberships past their end date and release their seats. Run daily."

    def handle(self, *args, **options):
        count = expire_overdue_memberships()
        self.stdout.write(self.style.SUCCESS(f"{count} membership(s) expired."))
