from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()
PASSWORD = "Lab-test-password-92!"


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("student", "student@example.test", PASSWORD)

    def test_login_and_logout(self):
        response = self.client.post("/accounts/login/", {"username": "student", "password": PASSWORD})
        self.assertRedirects(response, "/accounts/dashboard/")
        self.assertEqual(self.client.get("/accounts/me/").json(), {"username": "student", "role": "student"})
        self.assertContains(self.client.get("/accounts/dashboard/"), "Signed in as")
        self.assertEqual(self.client.get("/accounts/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/accounts/logout/"), "/accounts/login/")
        self.assertEqual(self.client.get("/accounts/me/").status_code, 401)

    def test_anonymous_access_is_blocked(self):
        self.assertRedirects(self.client.get("/accounts/dashboard/"), "/accounts/login/?next=/accounts/dashboard/")
        self.assertEqual(self.client.get("/accounts/me/").status_code, 401)

    def test_wrong_missing_and_inactive_credentials(self):
        for data in [{}, {"username": "student", "password": "wrong"}]:
            response = self.client.post("/accounts/login/", data)
            self.assertTrue(response.context["form"].errors)
            self.assertNotIn("_auth_user_id", self.client.session)
        self.user.is_active = False
        self.user.save()
        self.client.post("/accounts/login/", {"username": "student", "password": PASSWORD})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_external_next_url_is_rejected(self):
        response = self.client.post("/accounts/login/", {
            "username": "student", "password": PASSWORD, "next": "https://example.org/",
        })
        self.assertRedirects(response, "/accounts/dashboard/")

    def test_csrf_is_required_for_login_and_logout(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/accounts/login/", {"username": "student", "password": PASSWORD}).status_code, 403)
        client.get("/accounts/login/")
        token = client.cookies["csrftoken"].value
        response = client.post("/accounts/login/", {
            "username": "student", "password": PASSWORD, "csrfmiddlewaretoken": token,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.post("/accounts/logout/").status_code, 403)

    def test_private_response_is_not_cached(self):
        self.client.force_login(self.user)
        self.assertIn("no-store", self.client.get("/accounts/dashboard/").headers["Cache-Control"])
