from rest_framework import serializers

from .models import Cliente, EntidadeParceira, Lead, ProdutoContratado


class EntidadeParceiraSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.get_full_name", read_only=True)

    class Meta:
        model = EntidadeParceira
        fields = (
            "id", "usuario", "usuario_nome", "nome_entidade",
            "percentual_comissao", "ativo", "criado_em",
        )
        read_only_fields = ("id", "criado_em")

    def validate_percentual_comissao(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Percentual deve estar entre 0 e 100.")
        return value


class LeadSerializer(serializers.ModelSerializer):
    parceiro_nome = serializers.CharField(source="parceiro.nome_entidade", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    produto_display = serializers.CharField(source="get_produto_interesse_display", read_only=True)

    class Meta:
        model = Lead
        fields = (
            "id", "parceiro", "parceiro_nome", "operador",
            "nome", "email", "telefone",
            "produto_interesse", "produto_display",
            "status", "status_display",
            "criado_em", "atualizado_em",
        )
        read_only_fields = ("id", "criado_em", "atualizado_em")


class LeadStatusSerializer(serializers.ModelSerializer):
    """Serializer exclusivo para PATCH de status do lead."""

    class Meta:
        model = Lead
        fields = ("id", "status")
        read_only_fields = ("id",)


class ProdutoContratadoSerializer(serializers.ModelSerializer):
    produto_display = serializers.CharField(source="get_produto_display", read_only=True)

    class Meta:
        model = ProdutoContratado
        fields = ("id", "cliente", "produto", "produto_display", "valor", "status", "contratado_em")
        read_only_fields = ("id", "contratado_em")

    def validate_valor(self, value):
        if value <= 0:
            raise serializers.ValidationError("O valor deve ser maior que zero.")
        return value


class ClienteSerializer(serializers.ModelSerializer):
    produtos = ProdutoContratadoSerializer(many=True, read_only=True)

    class Meta:
        model = Cliente
        fields = (
            "id", "lead", "nome", "documento", "email",
            "telefone", "ativo", "ativado_em", "produtos",
        )
        read_only_fields = ("id", "ativado_em")

    def validate_documento(self, value):
        digits = "".join(c for c in value if c.isdigit())
        if len(digits) not in (11, 14):
            raise serializers.ValidationError("Documento deve ser CPF (11 dígitos) ou CNPJ (14 dígitos).")
        return value
