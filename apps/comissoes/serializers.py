from rest_framework import serializers

from .models import Comissao


class ComissaoSerializer(serializers.ModelSerializer):
    parceiro_nome = serializers.CharField(source="parceiro.nome_entidade", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Comissao
        fields = (
            "id", "parceiro", "parceiro_nome", "venda",
            "valor_venda", "percentual", "valor_comissao",
            "status", "status_display", "gerado_em",
        )
        read_only_fields = ("id", "gerado_em")
