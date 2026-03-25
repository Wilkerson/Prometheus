from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Usuario


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Token JWT customizado com dados do perfil."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["perfil"] = user.perfil
        token["nome"] = user.get_full_name() or user.username
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["perfil"] = self.user.perfil
        data["nome"] = self.user.get_full_name() or self.user.username
        data["email"] = self.user.email
        return data


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ("id", "username", "email", "first_name", "last_name", "perfil", "is_active")
        read_only_fields = ("id",)


class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Usuario
        fields = ("id", "username", "email", "first_name", "last_name", "perfil", "password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MeSerializer(serializers.ModelSerializer):
    """Dados do usuário logado."""

    class Meta:
        model = Usuario
        fields = ("id", "username", "email", "first_name", "last_name", "perfil", "date_joined")
        read_only_fields = fields
