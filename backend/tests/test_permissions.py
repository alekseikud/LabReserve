from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import User


class PermissionTests(TestCase):
    def test_role_access_matrix(self):
        for role, manager_status, admin_status in [
            ("student", 403, 403), ("manager", 200, 403), ("admin", 200, 200),
        ]:
            with self.subTest(role=role):
                user = User.objects.create_user(role, f"{role}@example.test", role=role)
                self.client.force_login(user)
                self.assertEqual(self.client.get("/accounts/dashboard/").status_code, 200)
                self.assertEqual(self.client.get("/accounts/manager/").status_code, manager_status)
                self.assertEqual(self.client.get("/accounts/administrator/").status_code, admin_status)

    def test_anonymous_role_pages_require_login(self):
        for url in ["/accounts/manager/", "/accounts/administrator/"]:
            self.assertRedirects(self.client.get(url), f"/accounts/login/?next={url}")

    def test_login_cannot_change_role(self):
        user = User.objects.create_user("student", "student@example.test", "Test-password-92!")
        self.client.post("/accounts/login/", {
            "username": user.username, "password": "Test-password-92!", "role": "admin",
        })
        self.assertEqual(self.client.get("/accounts/administrator/").status_code, 403)
        user.refresh_from_db()
        self.assertEqual(user.role, "student")

    def test_role_change_takes_effect_on_next_request(self):
        user = User.objects.create_user("manager", "manager@example.test", role="manager")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/accounts/manager/").status_code, 200)
        User.objects.filter(pk=user.pk).update(role="student")
        self.assertEqual(self.client.get("/accounts/manager/").status_code, 403)


class CreateAccountTests(TestCase):
    def create(self, username="student", email="student@example.test", role="student", passwords=None):
        with patch("accounts.management.commands.create_account.getpass", side_effect=passwords or ["Test-password-92!"] * 2):
            call_command("create_account", username, email, role=role, stdout=StringIO())

    def test_creates_each_role_with_hashed_password(self):
        for role in User.Role.values:
            self.create(role, f"{role}@example.test", role)
            user = User.objects.get(username=role)
            self.assertEqual(user.role, role)
            self.assertTrue(user.check_password("Test-password-92!"))

    def test_invalid_email_weak_password_and_mismatch(self):
        for options in [
            {"email": "invalid"}, {"passwords": ["123", "123"]},
            {"passwords": ["Test-password-92!", "different"]},
        ]:
            with self.subTest(options=options), self.assertRaises(CommandError):
                self.create(**options)
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_account_is_not_overwritten(self):
        self.create()
        with self.assertRaises(CommandError):
            self.create()
        self.assertEqual(User.objects.count(), 1)
