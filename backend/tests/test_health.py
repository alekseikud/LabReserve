from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase


class HealthTests(TestCase):
    def test_health_queries_real_database(self):
        with self.assertNumQueries(1):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_database_failure_is_generic_503(self):
        with patch("core.views.connection.cursor", side_effect=OperationalError("private")):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn(b"private", response.content)

    def test_health_is_read_only(self):
        self.assertEqual(self.client.post("/api/health").status_code, 405)

    def test_business_endpoints_do_not_exist_yet(self):
        for url in ["/api/reservations", "/api/equipment", "/api/login", "/admin/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
