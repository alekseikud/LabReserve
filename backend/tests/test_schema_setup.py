from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection
from django.test import TestCase

from core.schema import apply_schema


class SchemaSetupTests(TestCase):
    def test_check_reports_pending_sql_without_applying_it(self):
        with patch("core.management.commands.apply_sql_schema.pending_schema_files",
                   return_value=[SimpleNamespace(name="002_example.sql")]):
            with self.assertRaisesMessage(CommandError, "002_example.sql"):
                call_command("apply_sql_schema", check=True)

    def test_failed_sql_file_rolls_back_schema_and_version_record(self):
        file = SimpleNamespace(
            name="999_failure.sql",
            read_text=lambda encoding: "CREATE TABLE rollback_probe (id integer); SELECT 1 / 0;",
        )
        with patch("core.schema.pending_schema_files", return_value=[file]):
            with self.assertRaises(DatabaseError):
                apply_schema()
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('rollback_probe')")
            self.assertIsNone(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM sql_schema_versions WHERE filename = %s", [file.name])
            self.assertEqual(cursor.fetchone()[0], 0)
