from rest_framework import serializers

from .models import Cliente, EntidadeParceira, Lead, ProdutoContratado


class EntidadeParceiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntidadeParceira
        fields = ("id", "usuario", "nome_entidade", "percentual_comissao", "ativo", "criado_em")
        read_only_fields = ("id", "criado_em")


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = (
            "id", "parceiro", "operador", "nome", "email", "telefone",
            "produto_interesse", "status", "criado_em", "atualizado_em",
        )
        read_only_fields = ("id", "criado_em", "atualizado_em")


class ProdutoContratadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdutoContratado
        fields = ("id", "cliente", "produto", "valor", "status", "contratado_em")
        read_only_fields = ("id", "contratado_em")


class ClienteSerializer(serializers.ModelSerializer):
    produtos = ProdutoContratadoSerializer(many=True, read_only=True)

    class Meta:
        model = Cliente
        fields = ("id", "lead", "nome", "documento", "email", "telefone", "ativo", "ativado_em", "produtos")
        read_only_fields = ("id", "ativado_em")
