import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, TestCase, override_settings

User = get_user_model()
OLD_PASSWORD = "Old-test-password-92!"
NEW_PASSWORD = "New-test-password-63!"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("student", "student@example.test", OLD_PASSWORD)

    def request_link(self):
        response = self.client.post("/accounts/password-reset/", {"email": self.user.email}, HTTP_HOST="localhost:8080")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        link = re.search(r"http://localhost:8080(\S+)", mail.outbox[0].body)
        self.assertIsNotNone(link)
        return link.group(1)

    def test_reset_changes_password_and_link_cannot_be_reused(self):
        logged_in = Client()
        logged_in.login(username="student", password=OLD_PASSWORD)
        link = self.request_link()
        response = self.client.get(link)
        form_url = response.url
        self.assertContains(self.client.get(form_url), "Choose a new password")
        response = self.client.post(form_url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})
        self.assertRedirects(response, "/accounts/reset/done/")
        self.assertFalse(self.client.login(username="student", password=OLD_PASSWORD))
        self.assertTrue(self.client.login(username="student", password=NEW_PASSWORD))
        self.assertContains(Client().get(link), "invalid or has expired")
        self.assertEqual(logged_in.get("/accounts/me/").status_code, 401)

    def test_unknown_and_inactive_emails_have_same_public_result(self):
        known = self.client.post("/accounts/password-reset/", {"email": self.user.email}, follow=True)
        mail.outbox.clear()
        unknown = self.client.post("/accounts/password-reset/", {"email": "missing@example.test"}, follow=True)
        self.assertEqual(known.content, unknown.content)
        self.user.is_active = False
        self.user.save()
        inactive = self.client.post("/accounts/password-reset/", {"email": self.user.email}, follow=True)
        self.assertEqual(known.content, inactive.content)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_validation_and_csrf(self):
        response = self.client.post("/accounts/password-reset/", {"email": "invalid"})
        self.assertIn("email", response.context["form"].errors)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/accounts/password-reset/", {"email": self.user.email}).status_code, 403)

    def test_weak_and_mismatching_passwords_are_rejected(self):
        form_url = self.client.get(self.request_link()).url
        for first, second in [("123", "123"), (NEW_PASSWORD, "different")]:
            response = self.client.post(form_url, {"new_password1": first, "new_password2": second})
            self.assertTrue(response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))

    def test_invalid_and_expired_links(self):
        self.assertContains(self.client.get("/accounts/reset/bad/bad/"), "invalid or has expired")
        link = self.request_link()
        future = default_token_generator._now() + timedelta(hours=2)
        with patch.object(default_token_generator, "_now", return_value=future):
            self.assertContains(self.client.get(link), "invalid or has expired")
