from accounts.models import User
from booking.db import one, query


def fixtures():
    users = {role: User.objects.create_user(role, f"{role}@example.test", "Test-password-92!", role=role)
             for role in User.Role.values}
    lab = one("INSERT INTO inventory_laboratory (code, name, location) VALUES (%s, %s, %s) RETURNING *", ["A1", "Electronics", "Building A"])
    other_lab = one("INSERT INTO inventory_laboratory (code, name, location) VALUES (%s, %s, %s) RETURNING *", ["B1", "Physics", "Building B"])
    query("INSERT INTO inventory_laboratory_managers (laboratory_id, user_id) VALUES (%s, %s)", [lab["id"], users["manager"].pk])
    equipment = one("""INSERT INTO inventory_equipment (laboratory_id, asset_tag, name, category)
                       VALUES (%s, %s, %s, %s) RETURNING *""", [lab["id"], "OSC-1", "Oscilloscope", "Measurement"])
    other = one("""INSERT INTO inventory_equipment (laboratory_id, asset_tag, name, category, status)
                   VALUES (%s, %s, %s, %s, %s) RETURNING *""", [other_lab["id"], "LAS-1", "Laser", "Optics", "maintenance"])
    return users, lab, other_lab, equipment, other
