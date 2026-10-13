"""Small helpers for templates: Bootstrap form fields, status badges and money."""
from decimal import Decimal, InvalidOperation

from django import template
from django.forms import CheckboxInput, Select, SelectMultiple
from django.utils.html import format_html

register = template.Library()

BADGE_COLORS = {
    "success": ["active", "approved", "confirmed", "paid", "resolved", "allocated", "available"],
    "warning": ["pending", "reserved", "partial", "in_progress", "in progress"],
    "danger": ["rejected", "unpaid", "occupied", "expired"],
    "secondary": ["cancelled", "ended", "inactive", "deactivated"],
}


@register.filter
def bs(field):
    """Render a form field with the right Bootstrap class: {{ form.name|bs }}"""
    widget = field.field.widget
    if isinstance(widget, CheckboxInput):
        css = "form-check-input"
    elif isinstance(widget, (Select, SelectMultiple)):
        css = "form-select"
    else:
        css = "form-control"
    if field.errors:
        css += " is-invalid"
    existing = widget.attrs.get("class", "")
    return field.as_widget(attrs={"class": f"{existing} {css}".strip()})


@register.simple_tag
def status_badge(value, label=None):
    """{% status_badge booking.status booking.get_status_display %} -> coloured badge"""
    key = str(value).lower()
    color = next((name for name, words in BADGE_COLORS.items() if key in words), "secondary")
    return format_html('<span class="badge text-bg-{}">{}</span>', color, label or str(value).replace("_", " ").title())


@register.filter
def money(value):
    """Format a Decimal as Indian rupees: 1500 -> ₹1,500.00"""
    try:
        return f"₹{Decimal(value):,.2f}"
    except (InvalidOperation, TypeError, ValueError):
        return "₹0.00"
