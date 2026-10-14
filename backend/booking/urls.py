from django.urls import path

from . import management_views, views

urlpatterns = [
    path("equipment/", views.equipment_list, name="equipment_list"),
    path("equipment/<int:pk>/", views.equipment_detail, name="equipment_detail"),
    path("laboratories/", views.laboratory_list, name="laboratory_list"),
    path("equipment/<int:pk>/reserve/", views.reservation_create, name="reservation_create"),
    path("reservations/", views.reservation_list, name="reservation_list"),
    path("reservations/<int:pk>/cancel/", views.reservation_cancel, name="reservation_cancel"),
    path("manage/equipment/", management_views.equipment_manage, name="equipment_manage"),
    path("manage/equipment/new/", management_views.equipment_edit, name="equipment_create"),
    path("manage/equipment/<int:pk>/", management_views.equipment_edit, name="equipment_edit"),
    path("manage/reservations/", management_views.reservation_review, name="reservation_review"),
    path("manage/reservations/<int:pk>/", management_views.reservation_decide, name="reservation_decide"),
]
