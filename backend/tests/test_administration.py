from django.test import Client, TestCase

from accounts.models import User
from booking.db import query
from .booking_fixtures import fixtures


class AdministrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users, cls.lab, cls.other_lab, cls.equipment, cls.other = fixtures()

    def setUp(self):
        self.client.force_login(self.users["admin"])

    def test_create_lab_and_assign_manager(self):
        response = self.client.post("/workspace/admin/laboratories/new/", {
            "code": "C1", "name": "Chemistry", "location": "Building C", "managers": [self.users["manager"].pk],
        })
        self.assertRedirects(response, "/workspace/admin/laboratories/")
        self.assertEqual(len(query("SELECT * FROM inventory_laboratory_managers WHERE user_id = %s", [self.users["manager"].pk])), 2)

    def test_lab_validation_and_assignment_replacement(self):
        url = f"/workspace/admin/laboratories/{self.lab['id']}/"
        self.assertContains(self.client.post(url, {**self.lab, "code": "B1"}), "code is already used")
        self.assertContains(self.client.post(url, {**self.lab, "managers": [self.users["student"].pk]}), "Select a valid choice")
        self.assertEqual(self.client.post(url, {**self.lab, "location": "New building"}).status_code, 302)
        self.assertEqual(query("SELECT * FROM inventory_laboratory_managers"), [])

    def test_create_user_and_disable_existing_user(self):
        response = self.client.post("/workspace/admin/users/new/", {
            "username": "new-student", "email": "new@example.test", "role": "student",
            "password1": "New-student-password-53!", "password2": "New-student-password-53!",
        })
        self.assertRedirects(response, "/workspace/admin/users/")
        self.assertTrue(User.objects.get(username="new-student").check_password("New-student-password-53!"))
        manager = self.users["manager"]
        logged_in = Client()
        logged_in.force_login(manager)
        self.client.post(f"/workspace/admin/users/{manager.pk}/", {
            "username": manager.username, "email": manager.email, "role": "student",
        })
        self.assertEqual(logged_in.get("/accounts/me/").status_code, 401)
        self.assertEqual(query("SELECT * FROM inventory_laboratory_managers"), [])

    def test_cannot_remove_own_admin_access(self):
        admin = self.users["admin"]
        self.assertContains(self.client.post(f"/workspace/admin/users/{admin.pk}/", {
            "username": admin.username, "email": admin.email, "role": "student", "is_active": True,
        }), "cannot remove your own")
        admin.refresh_from_db()
        self.assertEqual(admin.role, "admin")

    def test_non_admin_and_csrf_protection(self):
        self.client.force_login(self.users["manager"])
        for url in ["/workspace/admin/users/", "/workspace/admin/users/new/", "/workspace/admin/laboratories/", "/workspace/admin/laboratories/new/"]:
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {}).status_code, 403)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.users["admin"])
        self.assertEqual(client.post("/workspace/admin/laboratories/new/", {}).status_code, 403)
