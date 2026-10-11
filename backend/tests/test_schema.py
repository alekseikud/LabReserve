from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from core.schema import apply_schema, pending_schema_files


def sql(statement, params=()):
    with connection.cursor() as cursor:
        cursor.execute(statement, params)
        return cursor.fetchall() if cursor.description else []


class SchemaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Only authentication uses the ORM. Domain fixtures use SQL.
        cls.owner = User.objects.create_user(username="student", email="student@example.test")
        cls.lab_id = sql(
            "INSERT INTO inventory_laboratory (code, name, location) VALUES (%s, %s, %s) RETURNING id",
            ["A101", "Electronics", "Building A"],
        )[0][0]
        cls.equipment_id = sql(
            """INSERT INTO inventory_equipment (laboratory_id, asset_tag, name, category)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            [cls.lab_id, "OSC-001", "Oscilloscope", "Measurement"],
        )[0][0]

    def setUp(self):
        # Check foreign keys inside each test rather than waiting for its rollback.
        sql("SET CONSTRAINTS ALL IMMEDIATE")

    def reservation(self, **changes):
        start = timezone.now()
        values = {
            "owner_id": self.owner.pk, "equipment_id": self.equipment_id,
            "purpose": "SQL schema test", "starts_at": start,
            "ends_at": start + timedelta(hours=1),
        }
        values.update(changes)
        return sql(
            """INSERT INTO reservations_reservation
               (owner_id, equipment_id, purpose, starts_at, ends_at)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            [values[key] for key in ("owner_id", "equipment_id", "purpose", "starts_at", "ends_at")],
        )[0][0]

    def test_user_role_defaults_to_student(self):
        self.assertEqual(self.owner.role, User.Role.STUDENT)

    def test_database_rejects_invalid_role(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=self.owner.pk).update(role="unknown")

    def test_unique_email(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="duplicate", email=self.owner.email)

    def test_django_authentication_still_works(self):
        user = User.objects.create_user(
            username="login-test", email="login@example.test", password="test-password-123!"
        )
        self.assertNotEqual(user.password, "test-password-123!")
        self.assertEqual(authenticate(username=user.username, password="test-password-123!"), user)
        self.assertIsNone(authenticate(username=user.username, password="wrong"))
        self.assertTrue(self.client.login(username=user.username, password="test-password-123!"))

    def test_laboratory_manager_link(self):
        manager = User.objects.create_user(
            username="manager", email="manager@example.test", role=User.Role.MANAGER
        )
        sql(
            "INSERT INTO inventory_laboratory_managers (laboratory_id, user_id) VALUES (%s, %s)",
            [self.lab_id, manager.pk],
        )
        self.assertEqual(sql(
            """SELECT l.code FROM inventory_laboratory l
               JOIN inventory_laboratory_managers m ON m.laboratory_id = l.id
               WHERE m.user_id = %s""", [manager.pk],
        ), [("A101",)])
        with self.assertRaises(IntegrityError), transaction.atomic():
            sql(
                "INSERT INTO inventory_laboratory_managers (laboratory_id, user_id) VALUES (%s, %s)",
                [self.lab_id, manager.pk],
            )

    def test_asset_tag_is_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            sql(
                """INSERT INTO inventory_equipment (laboratory_id, asset_tag, name, category)
                   VALUES (%s, %s, %s, %s)""",
                [self.lab_id, "OSC-001", "Other", "Measurement"],
            )

    def test_database_rejects_invalid_equipment_status(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            sql("UPDATE inventory_equipment SET status = %s WHERE id = %s", ["unknown", self.equipment_id])

    def test_laboratory_with_equipment_is_protected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            sql("DELETE FROM inventory_laboratory WHERE id = %s", [self.lab_id])

    def test_database_rejects_zero_and_negative_intervals(self):
        start = timezone.now()
        for end in [start, start - timedelta(hours=1)]:
            with self.subTest(end=end), self.assertRaises(IntegrityError), transaction.atomic():
                self.reservation(starts_at=start, ends_at=end)

    def test_reservation_relationships_and_protected_history(self):
        record_id = self.reservation()
        self.assertEqual(sql(
            "SELECT status, owner_id, equipment_id FROM reservations_reservation WHERE id = %s",
            [record_id],
        ), [("pending", self.owner.pk, self.equipment_id)])
        with self.assertRaises(IntegrityError), transaction.atomic():
            sql("DELETE FROM inventory_equipment WHERE id = %s", [self.equipment_id])
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.owner.delete()

    def test_database_rejects_invalid_reservation_status(self):
        record_id = self.reservation()
        with self.assertRaises(IntegrityError), transaction.atomic():
            sql("UPDATE reservations_reservation SET status = %s WHERE id = %s", ["unknown", record_id])

    def test_reservation_requires_existing_owner_and_equipment(self):
        for changes in [{"owner_id": -1}, {"equipment_id": -1}]:
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                self.reservation(**changes)

    def test_sql_defaults_and_update_timestamp(self):
        description, status, created, updated = sql(
            "SELECT description, status, created_at, updated_at FROM inventory_equipment WHERE id = %s",
            [self.equipment_id],
        )[0]
        self.assertEqual((description, status), ("", "available"))
        self.assertIsNotNone(created)
        sql("UPDATE inventory_equipment SET description = %s WHERE id = %s", ["Changed", self.equipment_id])
        self.assertGreaterEqual(sql(
            "SELECT updated_at FROM inventory_equipment WHERE id = %s", [self.equipment_id],
        )[0][0], updated)

    def test_parameter_values_are_not_executed_as_sql(self):
        purpose = "O'Brien'); DROP TABLE inventory_equipment; --"
        record_id = self.reservation(purpose=purpose)
        self.assertEqual(sql(
            "SELECT purpose FROM reservations_reservation WHERE id = %s", [record_id],
        ), [(purpose,)])
        self.assertEqual(sql("SELECT COUNT(*) FROM inventory_equipment"), [(1,)])

    def test_repeated_schema_application_keeps_records(self):
        self.assertEqual(apply_schema(), [])
        self.assertEqual(pending_schema_files(), [])
        self.assertEqual(sql("SELECT asset_tag FROM inventory_equipment"), [("OSC-001",)])

    def test_existing_tables_can_be_adopted_without_losing_records(self):
        # The former Django tables had Python defaults, not SQL defaults.
        sql("ALTER TABLE inventory_equipment ALTER COLUMN status DROP DEFAULT")
        sql("DELETE FROM sql_schema_versions WHERE filename = %s", ["001_initial.sql"])
        self.assertEqual(apply_schema(), ["001_initial.sql"])
        self.assertEqual(sql("SELECT asset_tag FROM inventory_equipment"), [("OSC-001",)])
        self.assertEqual(sql(
            """INSERT INTO inventory_equipment (laboratory_id, asset_tag, name, category)
               VALUES (%s, %s, %s, %s) RETURNING status""",
            [self.lab_id, "OSC-002", "Second oscilloscope", "Measurement"],
        ), [("available",)])
