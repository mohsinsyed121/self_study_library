from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user. Email is required and unique.

    - Library admins are users with is_staff=True.
    - Students are users with is_staff=False and a related StudentProfile.
    """

    email = models.EmailField("email address", unique=True)

    @property
    def is_library_admin(self):
        return self.is_staff

    def __str__(self):
        return self.get_full_name() or self.username
