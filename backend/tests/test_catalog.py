from django.test import TestCase

from .booking_fixtures import fixtures


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users, cls.lab, cls.other_lab, cls.equipment, cls.other = fixtures()

    def setUp(self):
        self.client.force_login(self.users["student"])

    def test_equipment_filters(self):
        for filters in [{"q": "osc"}, {"laboratory": self.lab["id"]}, {"category": "measure"}, {"status": "available"}]:
            with self.subTest(filters=filters):
                response = self.client.get("/workspace/equipment/", filters)
                self.assertContains(response, "Oscilloscope")
                self.assertNotContains(response, ">Laser<")

    def test_laboratory_filters(self):
        response = self.client.get("/workspace/laboratories/", {"location": "Building B"})
        self.assertContains(response, "Physics")
        self.assertNotContains(response, "Electronics")

    def test_invalid_filters_and_sql_input(self):
        self.assertContains(self.client.get("/workspace/equipment/", {"status": "invalid"}), "Select a valid choice")
        self.assertContains(self.client.get("/workspace/equipment/", {"q": "' OR 1=1 --"}), "No equipment found")
        self.assertContains(self.client.get("/workspace/laboratories/", {"q": "x" * 101}), "at most 100")

    def test_detail_and_missing_item(self):
        self.assertContains(self.client.get(f"/workspace/equipment/{self.equipment['id']}/"), "OSC-1")
        self.assertEqual(self.client.get("/workspace/equipment/999999/").status_code, 404)

    def test_anonymous_cannot_browse(self):
        self.client.logout()
        for url in ["/workspace/equipment/", "/workspace/laboratories/", f"/workspace/equipment/{self.equipment['id']}/"]:
            self.assertEqual(self.client.get(url).status_code, 302)
