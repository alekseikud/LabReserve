from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .models import User
from .permissions import roles_required


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


@never_cache
@roles_required(User.Role.MANAGER, User.Role.ADMIN)
@require_GET
def manager_page(request):
    return render(request, "accounts/role_page.html", {
        "heading": "Laboratory manager area",
        "description": "Manage equipment and review reservations for your assigned laboratories.",
        "manager_area": True,
    })


@never_cache
@roles_required(User.Role.ADMIN)
@require_GET
def administrator_page(request):
    return render(request, "accounts/role_page.html", {
        "heading": "Administrator area",
        "description": "Manage users, laboratories and laboratory assignments.",
        "admin_area": True,
    })
