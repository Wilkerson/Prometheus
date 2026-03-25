from rest_framework import serializers

from .models import Cliente, EntidadeParceira, Lead, LeadHistorico, ProdutoContratado


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


class LeadHistoricoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.get_full_name", read_only=True, default="")
    status_anterior_display = serializers.CharField(source="get_status_anterior_display", read_only=True)
    status_novo_display = serializers.CharField(source="get_status_novo_display", read_only=True)

    class Meta:
        model = LeadHistorico
        fields = (
            "id", "status_anterior", "status_anterior_display",
            "status_novo", "status_novo_display",
            "usuario", "usuario_nome", "observacao", "criado_em",
        )
        read_only_fields = ("id", "criado_em")


class LeadSerializer(serializers.ModelSerializer):
    parceiro_nome = serializers.CharField(source="parceiro.nome_entidade", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    produto_display = serializers.CharField(source="get_produto_interesse_display", read_only=True)
    historico = LeadHistoricoSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = (
            "id", "parceiro", "parceiro_nome", "operador",
            "nome", "email", "telefone",
            "produto_interesse", "produto_display",
            "status", "status_display",
            "criado_em", "atualizado_em", "historico",
        )
        read_only_fields = ("id", "criado_em", "atualizado_em")


class LeadListSerializer(serializers.ModelSerializer):
    """Serializer enxuto para listagens (sem histórico)."""
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


class LeadCreateParceiroSerializer(serializers.ModelSerializer):
    """Serializer para criação de lead pelo parceiro (parceiro é injetado na view)."""

    class Meta:
        model = Lead
        fields = ("id", "nome", "email", "telefone", "produto_interesse", "status", "criado_em")
        read_only_fields = ("id", "status", "criado_em")


class LeadStatusSerializer(serializers.Serializer):
    """Serializer para PATCH de status com validação de transição."""
    status = serializers.ChoiceField(choices=Lead.Status.choices)
    observacao = serializers.CharField(required=False, default="", allow_blank=True)

    def validate_status(self, value):
        lead = self.context.get("lead")
        if lead and not lead.pode_transitar_para(value):
            transicoes = Lead.TRANSICOES_VALIDAS.get(lead.status, ())
            permitidos = ", ".join(transicoes) if transicoes else "nenhum (status final)"
            raise serializers.ValidationError(
                f"Transição de '{lead.status}' para '{value}' não é permitida. "
                f"Transições válidas: {permitidos}."
            )
        return value


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
            "id", "lead", "nome", "documento", "cnpj", "email",
            "telefone", "arquivo", "ativo", "ativado_em", "produtos",
        )
        read_only_fields = ("id", "ativado_em")

    def validate_cnpj(self, value):
        digits = "".join(c for c in value if c.isdigit())
        if len(digits) != 14:
            raise serializers.ValidationError("CNPJ deve conter 14 dígitos.")
        return value

    def validate_documento(self, value):
        if not value:
            return value
        digits = "".join(c for c in value if c.isdigit())
        if len(digits) != 11:
            raise serializers.ValidationError("CPF deve conter 11 dígitos.")
        return value
