from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Usuario


class AuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = Usuario.objects.create_user(
            username="admin",
            email="admin@ruch.com",
            password="TestPass123!",
            perfil=Usuario.Perfil.SUPER_ADMIN,
            first_name="Admin",
        )

    def test_token_obtain(self):
        """Login deve retornar access, refresh, perfil, nome e email."""
        resp = self.client.post("/api/v1/auth/token/", {
            "username": "admin",
            "password": "TestPass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["perfil"], "super_admin")
        self.assertEqual(resp.data["email"], "admin@ruch.com")

    def test_token_refresh(self):
        """Refresh deve retornar novo access token."""
        resp = self.client.post("/api/v1/auth/token/", {
            "username": "admin",
            "password": "TestPass123!",
        })
        refresh = resp.data["refresh"]

        resp = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)

    def test_me_endpoint(self):
        """GET /auth/me/ deve retornar dados do usuário logado."""
        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "admin")
        self.assertEqual(resp.data["perfil"], "super_admin")

    def test_me_unauthenticated(self):
        """GET /auth/me/ sem token deve retornar 401."""
        resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PermissionsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Usuario.objects.create_user(
            username="admin", password="TestPass123!", perfil=Usuario.Perfil.SUPER_ADMIN,
        )
        self.operador = Usuario.objects.create_user(
            username="operador", password="TestPass123!", perfil=Usuario.Perfil.OPERADOR,
        )
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )

    def test_admin_can_list_usuarios(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/v1/auth/usuarios/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_operador_cannot_list_usuarios(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.get("/api/v1/auth/usuarios/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_parceiro_cannot_list_usuarios(self):
        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.get("/api/v1/auth/usuarios/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
