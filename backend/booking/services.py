from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .db import one


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
