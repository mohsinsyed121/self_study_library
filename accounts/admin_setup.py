import hmac
import os

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
@never_cache
def create_temporary_admin(request):
    expected_token = os.environ.get("ADMIN_SETUP_TOKEN", "")
    supplied_token = request.headers.get("X-Admin-Setup-Token", "")

    if not expected_token or not hmac.compare_digest(
        expected_token, supplied_token
    ):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    User = get_user_model()

    username = os.environ.get("INITIAL_ADMIN_USERNAME", "").strip()
    email = os.environ.get("INITIAL_ADMIN_EMAIL", "").strip()
    password = os.environ.get("INITIAL_ADMIN_PASSWORD", "")

    if not username or not email or not password:
        return JsonResponse(
            {"error": "Admin environment variables are incomplete"},
            status=500,
        )

    if User.objects.filter(username=username).exists():
        return JsonResponse(
            {"error": "Username already exists; no account changed"},
            status=409,
        )

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse(
            {"error": "Email already exists; no account changed"},
            status=409,
        )

    User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
    )

    return JsonResponse({"message": "Admin created successfully"})