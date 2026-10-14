from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import connections
from django.test import SimpleTestCase
from django.utils import timezone

from accounts.models import User
from booking.db import query
from booking.services import create_reservation
from .booking_fixtures import fixtures


class ConcurrentBookingTests(SimpleTestCase):
    # Committed fixtures are needed for separate connections. Clean only our rows;
    # Django's normal flush does not know about SQL-managed domain tables.
    databases = {"default"}

    def test_two_simultaneous_requests_only_create_one_booking(self):
        users, lab, other_lab, equipment, other = fixtures()
        gate = Barrier(2)
        start = timezone.now() + timedelta(days=2)

        def reserve():
            try:
                user = User.objects.get(pk=users["student"].pk)
                gate.wait(timeout=10)
                create_reservation(user, equipment["id"], {
                    "purpose": "Concurrent request", "starts_at": start, "ends_at": start + timedelta(hours=1),
                })
                return "created"
            except ValidationError:
                return "conflict"
            finally:
                connections.close_all()

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: reserve(), range(2)))
            self.assertCountEqual(results, ["created", "conflict"])
            self.assertEqual(len(query("SELECT id FROM reservations_reservation WHERE equipment_id = %s", [equipment["id"]])), 1)
        finally:
            query("DELETE FROM reservations_reservation WHERE equipment_id = ANY(%s)", [[equipment["id"], other["id"]]])
            query("DELETE FROM inventory_equipment WHERE id = ANY(%s)", [[equipment["id"], other["id"]]])
            query("DELETE FROM inventory_laboratory_managers WHERE laboratory_id = ANY(%s)", [[lab["id"], other_lab["id"]]])
            query("DELETE FROM inventory_laboratory WHERE id = ANY(%s)", [[lab["id"], other_lab["id"]]])
            User.objects.filter(pk__in=[user.pk for user in users.values()]).delete()
