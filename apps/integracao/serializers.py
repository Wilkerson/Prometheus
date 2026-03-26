from rest_framework import serializers

from apps.crm.models import Cliente


class ClienteIntegracaoSerializer(serializers.ModelSerializer):
    """Serializer para insercao de cliente via API Key (sistema externo)."""

    class Meta:
        model = Cliente
        fields = ("id", "nome", "cnpj", "email", "telefone", "endereco", "cep", "ativo")
        read_only_fields = ("id",)


class ClienteCallbackSerializer(serializers.Serializer):
    """Callback do sistema externo atualizando status do cliente."""
    cliente_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=[
        (Cliente.Status.CONCLUIDA, "Concluida"),
        (Cliente.Status.PERDIDA, "Perdida"),
    ])
    observacao = serializers.CharField(required=False, default="", allow_blank=True)
