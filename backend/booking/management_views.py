from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.permissions import roles_required
from .db import managed_laboratories, one, query
from .forms import EquipmentForm, ReservationFilter
from .services import cancel_reservation, require_laboratory_access, review_reservation, save_equipment
from .views import page_context


@never_cache
@roles_required("manager", "admin")
@require_GET
def equipment_manage(request):
    labs = managed_laboratories(request.user)
    rows = query("""SELECT e.*, l.code AS laboratory FROM inventory_equipment e
                    JOIN inventory_laboratory l ON l.id = e.laboratory_id
                    WHERE e.laboratory_id = ANY(%s) ORDER BY e.name, e.id""", [[lab["id"] for lab in labs]])
    return render(request, "booking/equipment_manage.html", {"labs": labs, **page_context(request, rows)})


@never_cache
@roles_required("manager", "admin")
@require_http_methods(["GET", "POST"])
def equipment_edit(request, pk=None):
    original = one("SELECT * FROM inventory_equipment WHERE id = %s", [pk]) if pk else None
    if original:
        require_laboratory_access(request.user, original["laboratory_id"])
    form = EquipmentForm(request.POST if request.method == "POST" else None, initial=original, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            save_equipment(request.user, form.cleaned_data, pk)
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error("asset_tag", "That asset tag is already used.")
        else:
            return redirect("equipment_manage")
    return render(request, "booking/form.html", {"form": form, "heading": "Edit equipment" if pk else "Add equipment"})


@never_cache
@roles_required("manager", "admin")
@require_GET
def reservation_review(request):
    form = ReservationFilter(request.GET)
    rows = []
    if form.is_valid():
        data = form.cleaned_data
        rows = query("""SELECT r.*, e.name AS equipment, u.username AS owner, l.code AS laboratory
                        FROM reservations_reservation r JOIN inventory_equipment e ON e.id = r.equipment_id
                        JOIN accounts_user u ON u.id = r.owner_id
                        JOIN inventory_laboratory l ON l.id = e.laboratory_id
                        WHERE e.laboratory_id = ANY(%s) AND (%s = '' OR r.status = %s) AND e.name ILIKE %s
                        ORDER BY r.starts_at DESC, r.id DESC""",
                     [[lab["id"] for lab in managed_laboratories(request.user)], data["status"], data["status"], f"%{data['q']}%"])
    for row in rows:
        row["can_cancel"] = request.user.role == "admin" and row["status"] in ("pending", "approved") and row["starts_at"] > timezone.now()
    return render(request, "booking/reservation_review.html", {"form": form, **page_context(request, rows)})


@never_cache
@roles_required("manager", "admin")
@require_POST
def reservation_decide(request, pk):
    try:
        if request.POST.get("decision") == "cancelled" and request.user.role == "admin":
            cancel_reservation(request.user, pk)
        else:
            review_reservation(request.user, pk, request.POST.get("decision"))
    except ValidationError as error:
        return render(request, "booking/action_error.html", {"error": " ".join(error.messages)}, status=400)
    return redirect("reservation_review")
