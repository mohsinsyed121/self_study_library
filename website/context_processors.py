from .models import SiteSettings


def site_settings(request):
    """Makes `site` (library name, logo, contact details...) available in every template."""
    return {"site": SiteSettings.load()}
