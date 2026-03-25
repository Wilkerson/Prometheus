from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Usuario
from .permissions import IsSuperAdmin
from .serializers import (
    CustomTokenObtainPairSerializer,
    MeSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login com JWT customizado — retorna perfil, nome e email."""

    serializer_class = CustomTokenObtainPairSerializer


class MeView(generics.RetrieveAPIView):
    """GET /api/v1/auth/me/ — dados do usuário logado."""

    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UsuarioViewSet(viewsets.ModelViewSet):
    """CRUD de usuários — somente Super Admin."""

    queryset = Usuario.objects.all()
    permission_classes = [IsSuperAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        return UsuarioSerializer
