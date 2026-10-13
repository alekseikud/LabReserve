from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@login_required
@require_GET
def dashboard(request):
    return render(request, "accounts/dashboard.html")


@never_cache
@require_GET
def current_user(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    return JsonResponse({"username": request.user.username, "role": request.user.role})
