from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Usuario


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Token JWT customizado com dados do usuario."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["nome"] = user.get_full_name() or user.username
        token["email"] = user.email
        token["is_parceiro"] = user.is_parceiro
        token["grupo"] = user.grupo_nome
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["nome"] = self.user.get_full_name() or self.user.username
        data["email"] = self.user.email
        data["is_parceiro"] = self.user.is_parceiro
        data["grupo"] = self.user.grupo_nome
        return data


class UsuarioSerializer(serializers.ModelSerializer):
    grupo = serializers.CharField(source="grupo_nome", read_only=True)

    class Meta:
        model = Usuario
        fields = ("id", "username", "email", "first_name", "last_name", "grupo", "is_active")
        read_only_fields = ("id",)


class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Usuario
        fields = ("id", "username", "email", "first_name", "last_name", "password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MeSerializer(serializers.ModelSerializer):
    grupo = serializers.CharField(source="grupo_nome", read_only=True)

    class Meta:
        model = Usuario
        fields = ("id", "username", "email", "first_name", "last_name", "grupo", "date_joined")
        read_only_fields = fields
