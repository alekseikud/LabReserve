"""Small helpers for parameterized SQL. Domain tables do not use ORM models."""
from django.db import connection
from django.http import Http404


def query(statement, params=()):
    with connection.cursor() as cursor:
        cursor.execute(statement, params)
        if cursor.description is None:
            return []
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]


def one(statement, params=()):
    rows = query(statement, params)
    if not rows:
        raise Http404("Record not found")
    return rows[0]


def laboratories():
    return query("SELECT * FROM inventory_laboratory ORDER BY code")


def managed_laboratories(user):
    if user.role == "admin":
        return laboratories()
    if user.role != "manager":
        return []
    return query("""SELECT l.* FROM inventory_laboratory l
                    JOIN inventory_laboratory_managers m ON m.laboratory_id = l.id
                    WHERE m.user_id = %s ORDER BY l.code""", [user.pk])
