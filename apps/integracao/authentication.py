from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import TokenIntegracao


class APIKeyAuthentication(BaseAuthentication):
    """Autenticação via header X-API-Key para sistemas externos."""

    def authenticate(self, request):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return None

        try:
            token = TokenIntegracao.objects.get(token=api_key, ativo=True)
        except TokenIntegracao.DoesNotExist:
            raise AuthenticationFailed("API Key inválida ou inativa.")

        return (None, token)
