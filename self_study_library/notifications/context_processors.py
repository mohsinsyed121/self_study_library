def unread_notifications(request):
    """Adds the unread count to every template (shown as a badge in the menu)."""
    user = request.user
    if user.is_authenticated and not user.is_staff:
        return {"unread_count": user.notifications.filter(is_read=False).count()}
    return {"unread_count": 0}
