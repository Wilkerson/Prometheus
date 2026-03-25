from rest_framework import serializers

from apps.crm.models import Cliente


class ClienteIntegracaoSerializer(serializers.ModelSerializer):
    """Serializer para inserção de cliente via API Key (sistema externo)."""

    class Meta:
        model = Cliente
        fields = ("id", "lead", "nome", "documento", "email", "telefone", "ativo", "ativado_em")
        read_only_fields = ("id", "ativado_em")
