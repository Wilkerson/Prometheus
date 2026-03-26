from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Usuario
from .permissions import IsSuperUser
from .serializers import (
    CustomTokenObtainPairSerializer,
    MeSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login com JWT customizado — retorna grupo, nome e email."""

    serializer_class = CustomTokenObtainPairSerializer


class MeView(generics.RetrieveAPIView):
    """GET /api/v1/auth/me/ — dados do usuario logado."""

    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UsuarioViewSet(viewsets.ModelViewSet):
    """CRUD de usuarios — somente superusuario."""

    queryset = Usuario.objects.all()
    permission_classes = [IsSuperUser]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        return UsuarioSerializer
