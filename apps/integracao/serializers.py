from rest_framework import serializers

from apps.crm.models import Cliente, Lead


class ClienteIntegracaoSerializer(serializers.ModelSerializer):
    """Serializer para inserção de cliente via API Key (sistema externo)."""

    class Meta:
        model = Cliente
        fields = ("id", "lead", "nome", "cnpj", "email", "telefone", "endereco", "cep", "ativo", "ativado_em")
        read_only_fields = ("id", "ativado_em")


class LeadCallbackSerializer(serializers.Serializer):
    """Serializer para callback do sistema externo atualizando status do lead."""
    lead_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=[
        (Lead.Status.CONCLUIDA, "Concluída"),
        (Lead.Status.PERDIDA, "Perdida"),
    ])
    observacao = serializers.CharField(required=False, default="", allow_blank=True)
