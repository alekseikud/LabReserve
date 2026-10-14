from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .db import managed_laboratories, one, query


def create_reservation(user, equipment_id, data):
    try:
        with transaction.atomic():
            equipment = one("SELECT * FROM inventory_equipment WHERE id = %s FOR UPDATE", [equipment_id])
            if equipment["status"] != "available":
                raise ValidationError("This equipment is not available for booking.")
            if data["starts_at"] <= timezone.now() or data["ends_at"] <= data["starts_at"]:
                raise ValidationError("Choose a valid future time interval.")
            return one("""INSERT INTO reservations_reservation
                (owner_id, equipment_id, purpose, starts_at, ends_at)
                VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                [user.pk, equipment_id, data["purpose"], data["starts_at"], data["ends_at"]])
    except IntegrityError as error:
        if getattr(getattr(error.__cause__, "diag", None), "constraint_name", None) == "reservation_no_overlap":
            raise ValidationError("This time overlaps an existing reservation. Choose another time.") from error
        raise


@transaction.atomic
def cancel_reservation(user, pk):
    reservation = one("SELECT * FROM reservations_reservation WHERE id = %s FOR UPDATE", [pk])
    if reservation["owner_id"] != user.pk and user.role != "admin":
        raise PermissionDenied
    if reservation["status"] not in ("pending", "approved") or reservation["starts_at"] <= timezone.now():
        raise ValidationError("Only future pending or approved reservations can be cancelled.")
    query("UPDATE reservations_reservation SET status = 'cancelled' WHERE id = %s", [pk])


def require_laboratory_access(user, laboratory_id):
    if laboratory_id not in {lab["id"] for lab in managed_laboratories(user)}:
        raise PermissionDenied


@transaction.atomic
def review_reservation(user, pk, decision):
    # Lock equipment before the reservation, matching equipment edits and new bookings.
    record = one("SELECT equipment_id FROM reservations_reservation WHERE id = %s", [pk])
    equipment = one("SELECT * FROM inventory_equipment WHERE id = %s FOR UPDATE", [record["equipment_id"]])
    require_laboratory_access(user, equipment["laboratory_id"])
    reservation = one("SELECT * FROM reservations_reservation WHERE id = %s FOR UPDATE", [pk])
    if decision not in ("approved", "rejected"):
        raise ValidationError("Choose approve or reject.")
    if reservation["status"] != "pending":
        raise ValidationError("Only pending requests can be reviewed.")
    if decision == "approved" and (equipment["status"] != "available" or reservation["starts_at"] <= timezone.now()):
        raise ValidationError("Cannot approve unavailable equipment or a booking that has started.")
    query("UPDATE reservations_reservation SET status = %s WHERE id = %s", [decision, pk])


@transaction.atomic
def save_equipment(user, data, pk=None):
    require_laboratory_access(user, data["laboratory_id"])
    if pk is not None:
        original = one("SELECT * FROM inventory_equipment WHERE id = %s FOR UPDATE", [pk])
        require_laboratory_access(user, original["laboratory_id"])
        if data["status"] != "available" or data["laboratory_id"] != original["laboratory_id"]:
            if query("""SELECT id FROM reservations_reservation WHERE equipment_id = %s
                        AND status IN ('pending', 'approved') AND ends_at > %s""", [pk, timezone.now()]):
                raise ValidationError("Resolve active reservations before moving or disabling this equipment.")
    values = [data[key] for key in ("laboratory_id", "asset_tag", "name", "category", "description", "status")]
    if pk is None:
        return one("""INSERT INTO inventory_equipment (laboratory_id, asset_tag, name, category, description, status)
                      VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""", values)
    return one("""UPDATE inventory_equipment SET laboratory_id = %s, asset_tag = %s, name = %s,
                  category = %s, description = %s, status = %s WHERE id = %s RETURNING *""", values + [pk])
