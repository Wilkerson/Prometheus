from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Usuario


class AuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = Usuario.objects.create_superuser(
            username="admin",
            email="admin@ruch.com",
            password="TestPass123!",
            first_name="Admin",
        )

    def test_token_obtain(self):
        """Login deve retornar access, refresh, nome e email."""
        resp = self.client.post("/api/v1/auth/token/", {
            "username": "admin",
            "password": "TestPass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["email"], "admin@ruch.com")

    def test_token_refresh(self):
        resp = self.client.post("/api/v1/auth/token/", {
            "username": "admin",
            "password": "TestPass123!",
        })
        refresh = resp.data["refresh"]
        resp = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)

    def test_me_endpoint(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "admin")

    def test_me_unauthenticated(self):
        resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PermissionsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Usuario.objects.create_superuser(
            username="admin", password="TestPass123!",
        )
        self.regular = Usuario.objects.create_user(
            username="regular", password="TestPass123!",
        )

    def test_superuser_can_list_usuarios(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/v1/auth/usuarios/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_regular_cannot_list_usuarios(self):
        self.client.force_authenticate(user=self.regular)
        resp = self.client.get("/api/v1/auth/usuarios/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
