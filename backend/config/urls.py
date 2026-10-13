from django.urls import include, path

from core.views import health

urlpatterns = [
    path("api/health", health, name="health"),
    path("accounts/", include("accounts.urls")),
]
