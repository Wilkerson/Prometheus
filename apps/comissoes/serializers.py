from rest_framework import serializers

from .models import Comissao


class ComissaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comissao
        fields = (
            "id", "parceiro", "venda", "valor_venda",
            "percentual", "valor_comissao", "status", "gerado_em",
        )
        read_only_fields = ("id", "gerado_em")
