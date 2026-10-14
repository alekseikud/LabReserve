from django.urls import path

from . import views

urlpatterns = [
    path("equipment/", views.equipment_list, name="equipment_list"),
    path("equipment/<int:pk>/", views.equipment_detail, name="equipment_detail"),
    path("laboratories/", views.laboratory_list, name="laboratory_list"),
    path("equipment/<int:pk>/reserve/", views.reservation_create, name="reservation_create"),
    path("reservations/", views.reservation_list, name="reservation_list"),
]
