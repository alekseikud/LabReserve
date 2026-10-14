from django.urls import path

from . import admin_views, management_views, views

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
    path("admin/laboratories/", admin_views.laboratory_manage, name="laboratory_manage"),
    path("admin/laboratories/new/", admin_views.laboratory_edit, name="laboratory_create"),
    path("admin/laboratories/<int:pk>/", admin_views.laboratory_edit, name="laboratory_edit"),
    path("admin/users/", admin_views.user_manage, name="user_manage"),
    path("admin/users/new/", admin_views.user_edit, name="user_create"),
    path("admin/users/<int:pk>/", admin_views.user_edit, name="user_edit"),
]
