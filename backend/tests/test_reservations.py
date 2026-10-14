from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone

from booking.db import query
from booking.services import create_reservation
from .booking_fixtures import fixtures


class ReservationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users, cls.lab, cls.other_lab, cls.equipment, cls.other = fixtures()

    def setUp(self):
        self.client.force_login(self.users["student"])
        self.start = timezone.now() + timedelta(days=2)
        self.data = {"purpose": "Lab exercise", "starts_at": self.start, "ends_at": self.start + timedelta(hours=1)}

    def test_create_is_pending_and_owner_is_taken_from_session(self):
        response = self.client.post(f"/workspace/equipment/{self.equipment['id']}/reserve/", {
            **self.data, "owner_id": self.users["admin"].pk, "status": "approved",
        })
        self.assertRedirects(response, "/workspace/reservations/")
        row = query("SELECT * FROM reservations_reservation")[0]
        self.assertEqual(row["owner_id"], self.users["student"].pk)
        self.assertEqual(row["status"], "pending")

    def test_overlap_rejected_but_adjacent_slot_allowed(self):
        create_reservation(self.users["student"], self.equipment["id"], self.data)
        with self.assertRaises(ValidationError):
            create_reservation(self.users["admin"], self.equipment["id"], self.data)
        create_reservation(self.users["student"], self.equipment["id"], {
            **self.data, "starts_at": self.data["ends_at"], "ends_at": self.data["ends_at"] + timedelta(hours=1),
        })
        self.assertEqual(len(query("SELECT id FROM reservations_reservation")), 2)

    def test_database_itself_rejects_overlaps(self):
        create_reservation(self.users["student"], self.equipment["id"], self.data)
        with self.assertRaises(IntegrityError), transaction.atomic():
            query("""INSERT INTO reservations_reservation (owner_id, equipment_id, purpose, starts_at, ends_at)
                     VALUES (%s, %s, %s, %s, %s)""", [self.users["admin"].pk, self.equipment["id"], "Direct SQL", self.start, self.data["ends_at"]])

    def test_unavailable_and_invalid_time_are_rejected(self):
        with self.assertRaises(ValidationError):
            create_reservation(self.users["student"], self.other["id"], self.data)
        url = f"/workspace/equipment/{self.equipment['id']}/reserve/"
        for changes in [{"purpose": " "}, {"ends_at": self.start}, {"starts_at": timezone.now() - timedelta(days=1)}]:
            response = self.client.post(url, {**self.data, **changes})
            self.assertTrue(response.context["form"].errors)
        self.assertEqual(query("SELECT id FROM reservations_reservation"), [])

    def test_list_is_private_and_filterable(self):
        create_reservation(self.users["student"], self.equipment["id"], self.data)
        self.assertContains(self.client.get("/workspace/reservations/", {"status": "pending"}), "Lab exercise")
        self.assertNotContains(self.client.get("/workspace/reservations/", {"status": "approved"}), "Lab exercise")
        self.client.force_login(self.users["manager"])
        self.assertNotContains(self.client.get("/workspace/reservations/"), "Lab exercise")
        self.assertNotContains(self.client.get(f"/workspace/equipment/{self.equipment['id']}/"), "Lab exercise")

    def test_creation_requires_csrf_and_login(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.users["student"])
        url = f"/workspace/equipment/{self.equipment['id']}/reserve/"
        self.assertEqual(client.post(url, self.data).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.post(url, self.data).status_code, 302)
