from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, RequestFactory, TestCase
from django.utils import timezone

from accounts.models import User
from booking.admin_views import user_edit
from booking.db import managed_laboratories, query
from booking.forms import EquipmentForm, LaboratoryForm, ReservationForm
from booking.services import create_reservation
from .booking_fixtures import fixtures


class QualityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users, cls.lab, cls.other_lab, cls.equipment, cls.other = fixtures()

    def setUp(self):
        self.client.force_login(self.users["admin"])
        start = timezone.now() + timedelta(days=2)
        self.data = {"purpose": "Private exercise", "starts_at": start, "ends_at": start + timedelta(hours=1)}

    def reserve(self):
        return create_reservation(self.users["student"], self.equipment["id"], self.data)

    def test_blank_email_rejected_by_terminal_and_web_forms(self):
        with patch("accounts.management.commands.create_account.getpass", return_value="Valid-test-password-93!"):
            with self.assertRaises(CommandError):
                call_command("create_account", "no-email", "", stdout=StringIO())
        student = self.users["student"]
        response = self.client.post(f"/workspace/admin/users/{student.pk}/", {
            "username": student.username, "email": "", "role": "student", "is_active": True,
        })
        self.assertFormError(response.context["form"], "email", "This field is required.")
        student.refresh_from_db()
        self.assertEqual(student.email, "student@example.test")

    def test_stale_admin_request_cannot_edit_after_role_revoked(self):
        actor = self.users["admin"]
        request = RequestFactory().post(f"/workspace/admin/users/{self.users['student'].pk}/", {
            "username": "changed", "email": "changed@example.test", "role": "admin", "is_active": True,
        })
        request.user = actor
        User.objects.filter(pk=actor.pk).update(role="student")
        with self.assertRaises(PermissionDenied):
            user_edit(request, pk=self.users["student"].pk)
        self.assertFalse(User.objects.filter(username="changed").exists())

    def test_csrf_blocks_all_management_mutations(self):
        record = self.reserve()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.users["admin"])
        paths = [
            "/workspace/manage/equipment/new/", f"/workspace/manage/equipment/{self.equipment['id']}/",
            f"/workspace/manage/reservations/{record['id']}/", "/workspace/admin/laboratories/new/",
            f"/workspace/admin/laboratories/{self.lab['id']}/", "/workspace/admin/users/new/",
            f"/workspace/admin/users/{self.users['student'].pk}/",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(client.post(path, {}).status_code, 403)

    def test_anonymous_cannot_open_any_management_page(self):
        self.client.logout()
        for path in ["/workspace/manage/equipment/", "/workspace/manage/equipment/new/", "/workspace/manage/reservations/",
                     "/workspace/admin/laboratories/", "/workspace/admin/laboratories/new/", "/workspace/admin/users/", "/workspace/admin/users/new/"]:
            self.assertEqual(self.client.get(path).status_code, 302)

    def test_missing_records_are_404(self):
        for path in ["/workspace/equipment/999999/reserve/", "/workspace/manage/equipment/999999/",
                     "/workspace/admin/users/999999/", "/workspace/admin/laboratories/999999/"]:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post("/workspace/manage/reservations/999999/", {"decision": "approved"}).status_code, 404)

    def test_manager_cannot_forge_cross_lab_equipment_update(self):
        self.client.force_login(self.users["manager"])
        response = self.client.post(f"/workspace/manage/equipment/{self.other['id']}/", {
            **self.other, "laboratory_id": self.lab["id"], "name": "Taken over",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(query("SELECT name FROM inventory_equipment WHERE id = %s", [self.other["id"]])[0]["name"], "Laser")
        self.assertEqual(managed_laboratories(self.users["student"]), [])

    def test_admin_and_unassigned_manager_equipment_lists(self):
        response = self.client.get("/workspace/manage/equipment/")
        self.assertContains(response, "Oscilloscope")
        self.assertContains(response, "Laser")
        query("DELETE FROM inventory_laboratory_managers")
        self.client.force_login(self.users["manager"])
        self.assertContains(self.client.get("/workspace/manage/equipment/"), "No laboratories are assigned")

    def test_invalid_review_decision_and_started_approval(self):
        record = self.reserve()
        path = f"/workspace/manage/reservations/{record['id']}/"
        self.assertContains(self.client.post(path, {"decision": "anything"}), "Choose approve or reject", status_code=400)
        query("UPDATE reservations_reservation SET starts_at = %s WHERE id = %s", [timezone.now() - timedelta(hours=1), record["id"]])
        self.assertContains(self.client.post(path, {"decision": "approved"}), "has started", status_code=400)
        self.assertEqual(query("SELECT status FROM reservations_reservation")[0]["status"], "pending")

    def test_unavailable_approval_and_reservation_form_feedback(self):
        record = self.reserve()
        query("UPDATE inventory_equipment SET status = 'maintenance' WHERE id = %s", [self.equipment["id"]])
        self.assertEqual(self.client.post(f"/workspace/manage/reservations/{record['id']}/", {"decision": "approved"}).status_code, 400)
        self.assertContains(self.client.post(f"/workspace/equipment/{self.other['id']}/reserve/", self.data), "not available for booking")

    def test_invalid_filters_show_errors_without_exposing_records(self):
        self.reserve()
        self.client.force_login(self.users["student"])
        response = self.client.get("/workspace/reservations/", {"status": "bad"})
        self.assertContains(response, "Select a valid choice")
        self.assertNotContains(response, "Private exercise")
        self.client.force_login(self.users["manager"])
        self.assertContains(self.client.get("/workspace/manage/reservations/", {"status": "bad"}), "Select a valid choice")

    def test_equipment_can_be_disabled_or_moved_when_unbooked(self):
        data = {**self.equipment, "laboratory_id": self.other_lab["id"], "status": "retired"}
        self.assertEqual(self.client.post(f"/workspace/manage/equipment/{self.equipment['id']}/", data).status_code, 302)
        row = query("SELECT status, laboratory_id FROM inventory_equipment WHERE id = %s", [self.equipment["id"]])[0]
        self.assertEqual(row, {"status": "retired", "laboratory_id": self.other_lab["id"]})

    def test_required_fields_and_length_limits(self):
        self.assertFalse(EquipmentForm({}, user=self.users["admin"]).is_valid())
        self.assertFalse(LaboratoryForm({}).is_valid())
        self.assertFalse(EquipmentForm({**self.equipment, "asset_tag": "X" * 41}, user=self.users["admin"]).is_valid())
        self.assertFalse(ReservationForm({**self.data, "purpose": "X" * 501}).is_valid())
        self.assertFalse(ReservationForm({**self.data, "starts_at": "not a date"}).is_valid())

    def test_ambiguous_and_nonexistent_warsaw_times_are_rejected(self):
        for start, end in [("2027-03-28T02:30", "2027-03-28T04:00"), ("2027-10-31T02:30", "2027-10-31T04:00")]:
            form = ReservationForm({"purpose": "DST check", "starts_at": start, "ends_at": end})
            self.assertFalse(form.is_valid())
            self.assertIn("starts_at", form.errors)

    def test_names_are_html_escaped(self):
        query("UPDATE inventory_equipment SET name = %s WHERE id = %s", ["<script>alert(1)</script>", self.equipment["id"]])
        response = self.client.get(f"/workspace/equipment/{self.equipment['id']}/")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_pagination_preserves_filters_and_handles_bad_page(self):
        for index in range(23):
            query("""INSERT INTO inventory_equipment (laboratory_id, asset_tag, name, category)
                     VALUES (%s, %s, %s, %s)""", [self.lab["id"], f"PAGE-{index}", "Paged equipment", "Measurement"])
        response = self.client.get("/workspace/equipment/", {"q": "Paged", "page": 2})
        self.assertEqual(len(response.context["page"]), 3)
        self.assertContains(response, "q=Paged&amp;page=1")
        self.assertEqual(self.client.get("/workspace/equipment/", {"page": "invalid"}).status_code, 200)

    def test_user_edit_validation_does_not_change_existing_account(self):
        student = self.users["student"]
        path = f"/workspace/admin/users/{student.pk}/"
        for changes in [{"role": "superuser"}, {"email": self.users["admin"].email}, {"username": self.users["admin"].username}]:
            response = self.client.post(path, {"username": student.username, "email": student.email, "role": "student", "is_active": True, **changes})
            self.assertTrue(response.context["form"].errors)
        student.refresh_from_db()
        self.assertEqual(student.role, "student")

    def test_service_rechecks_time_before_inserting(self):
        with self.assertRaises(ValidationError):
            create_reservation(self.users["student"], self.equipment["id"], {**self.data, "starts_at": timezone.now() - timedelta(days=1)})
