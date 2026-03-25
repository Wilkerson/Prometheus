from rest_framework import generics, permissions

from .authentication import APIKeyAuthentication
from .serializers import ClienteIntegracaoSerializer


class ClienteIntegracaoCreateView(generics.CreateAPIView):
    """POST /api/v1/integracao/cliente/ — cria cliente via API Key."""

    serializer_class = ClienteIntegracaoSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        serializer.save()
