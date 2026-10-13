from django.conf import settings
from django.core.paginator import Paginator


def paginate(request, queryset_or_list, per_page=None):
    """Return one page of results using ?page=N from the URL."""
    paginator = Paginator(queryset_or_list, per_page or settings.PAGINATE_BY)
    return paginator.get_page(request.GET.get("page"))
