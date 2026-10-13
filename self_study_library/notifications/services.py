"""Call notify() from any app when something important happens to a user."""
from .models import Notification


def notify(user, title, message):
    return Notification.objects.create(user=user, title=title, message=message)
