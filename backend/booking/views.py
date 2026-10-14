from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from .db import one, query
from .forms import EquipmentFilter, LaboratoryFilter, ReservationFilter, ReservationForm
from .services import create_reservation


def page_context(request, rows):
    params = request.GET.copy()
    params.pop("page", None)
    return {"page": Paginator(rows, 20).get_page(request.GET.get("page")), "filters": params.urlencode()}


@never_cache
@login_required
@require_GET
def equipment_list(request):
    form = EquipmentFilter(request.GET)
    rows = []
    if form.is_valid():
        data = form.cleaned_data
        rows = query("""
            SELECT e.*, l.code AS laboratory FROM inventory_equipment e
            JOIN inventory_laboratory l ON l.id = e.laboratory_id
            WHERE (e.name ILIKE %s OR e.asset_tag ILIKE %s)
              AND (%s = '' OR e.laboratory_id = NULLIF(%s, '')::bigint)
              AND e.category ILIKE %s AND (%s = '' OR e.status = %s)
            ORDER BY e.name, e.id
        """, [f"%{data['q']}%", f"%{data['q']}%", data["laboratory"], data["laboratory"],
              f"%{data['category']}%", data["status"], data["status"]])
    return render(request, "booking/equipment_list.html", {"form": form, **page_context(request, rows)})


@never_cache
@login_required
@require_GET
def laboratory_list(request):
    form = LaboratoryFilter(request.GET)
    rows = []
    if form.is_valid():
        data = form.cleaned_data
        rows = query("""
            SELECT l.*, COUNT(e.id) AS equipment_count FROM inventory_laboratory l
            LEFT JOIN inventory_equipment e ON e.laboratory_id = l.id
            WHERE (l.code ILIKE %s OR l.name ILIKE %s) AND l.location ILIKE %s
            GROUP BY l.id ORDER BY l.code
        """, [f"%{data['q']}%", f"%{data['q']}%", f"%{data['location']}%"])
    return render(request, "booking/laboratory_list.html", {"form": form, **page_context(request, rows)})


@never_cache
@login_required
@require_GET
def equipment_detail(request, pk):
    equipment = one("""SELECT e.*, l.code AS laboratory FROM inventory_equipment e
                       JOIN inventory_laboratory l ON l.id = e.laboratory_id WHERE e.id = %s""", [pk])
    slots = query("""SELECT starts_at, ends_at, status FROM reservations_reservation
                     WHERE equipment_id = %s AND status IN ('pending', 'approved') AND ends_at > %s
                     ORDER BY starts_at""", [pk, timezone.now()])
    return render(request, "booking/equipment_detail.html", {"equipment": equipment, "slots": slots})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def reservation_create(request, pk):
    equipment = one("SELECT * FROM inventory_equipment WHERE id = %s", [pk])
    form = ReservationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            create_reservation(request.user, pk, form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            return redirect("reservation_list")
    return render(request, "booking/form.html", {"form": form, "heading": f"Reserve {equipment['name']}", "button": "Request reservation"})


@never_cache
@login_required
@require_GET
def reservation_list(request):
    form = ReservationFilter(request.GET)
    rows = []
    if form.is_valid():
        data = form.cleaned_data
        rows = query("""SELECT r.*, e.name AS equipment FROM reservations_reservation r
                        JOIN inventory_equipment e ON e.id = r.equipment_id
                        WHERE r.owner_id = %s AND (%s = '' OR r.status = %s) AND e.name ILIKE %s
                        ORDER BY r.starts_at DESC, r.id DESC""",
                     [request.user.pk, data["status"], data["status"], f"%{data['q']}%"])
    return render(request, "booking/reservation_list.html", {"form": form, **page_context(request, rows)})
