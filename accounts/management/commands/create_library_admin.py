
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the initial library administrator if one does not exist."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not all([username, email, password]):
            raise CommandError(
                "Set DJANGO_SUPERUSER_USERNAME, "
                "DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD."
            )

        User = get_user_model()

        user = User.objects.filter(username=username).first()

        if user:
            self.stdout.write(
                self.style.WARNING(
                    f"User '{username}' already exists. No changes made."
                )
            )
            return

        if User.objects.filter(email=email).exists():
            raise CommandError("This email address is already registered.")

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS("Library administrator created successfully.")
        )
