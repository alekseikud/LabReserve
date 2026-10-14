from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from booking.db import query
from booking.services import create_reservation
from .booking_fixtures import fixtures


class ManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users, cls.lab, cls.other_lab, cls.equipment, cls.other = fixtures()

    def setUp(self):
        self.client.force_login(self.users["manager"])
        start = timezone.now() + timedelta(days=2)
        self.reservation = create_reservation(self.users["student"], self.equipment["id"], {
            "purpose": "Private request", "starts_at": start, "ends_at": start + timedelta(hours=1),
        })

    def test_manager_approves_once(self):
        url = f"/workspace/manage/reservations/{self.reservation['id']}/"
        self.assertContains(self.client.get("/workspace/manage/reservations/"), "Private request")
        self.assertEqual(self.client.post(url, {"decision": "approved"}).status_code, 302)
        self.assertEqual(query("SELECT status FROM reservations_reservation")[0]["status"], "approved")
        self.assertEqual(self.client.post(url, {"decision": "rejected"}).status_code, 400)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_reject_releases_slot(self):
        self.client.post(f"/workspace/manage/reservations/{self.reservation['id']}/", {"decision": "rejected"})
        create_reservation(self.users["student"], self.equipment["id"], self.reservation)
        self.assertEqual(len(query("SELECT id FROM reservations_reservation")), 2)

    def test_unassigned_manager_cannot_read_or_approve(self):
        query("DELETE FROM inventory_laboratory_managers")
        self.assertNotContains(self.client.get("/workspace/manage/reservations/"), "Private request")
        self.assertEqual(self.client.post(f"/workspace/manage/reservations/{self.reservation['id']}/", {"decision": "approved"}).status_code, 403)

    def test_students_cannot_manage(self):
        self.client.force_login(self.users["student"])
        for url in ["/workspace/manage/equipment/", "/workspace/manage/equipment/new/", "/workspace/manage/reservations/"]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_equipment_scope_duplicates_and_active_booking_guard(self):
        data = {**self.equipment, "description": "Changed"}
        url = f"/workspace/manage/equipment/{self.equipment['id']}/"
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertContains(self.client.post(url, {**data, "status": "maintenance"}), "Resolve active reservations")
        self.assertContains(self.client.post(url, {**data, "laboratory_id": self.other_lab["id"]}), "Select a valid choice")
        self.assertEqual(self.client.get(f"/workspace/manage/equipment/{self.other['id']}/").status_code, 403)
        self.assertContains(self.client.post("/workspace/manage/equipment/new/", data), "asset tag is already used")
        self.assertEqual(self.client.post("/workspace/manage/equipment/new/", {**data, "asset_tag": "NEW-1"}).status_code, 302)

    def test_admin_can_cancel_any_future_booking(self):
        self.client.force_login(self.users["admin"])
        self.assertEqual(self.client.post(f"/workspace/manage/reservations/{self.reservation['id']}/", {"decision": "cancelled"}).status_code, 302)
        self.assertEqual(query("SELECT status FROM reservations_reservation")[0]["status"], "cancelled")
