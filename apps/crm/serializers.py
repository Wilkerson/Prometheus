from rest_framework import serializers

from .models import Cliente, ClienteHistorico, EntidadeParceira, ProdutoContratado


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


class ClienteHistoricoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.get_full_name", read_only=True, default="")
    status_anterior_display = serializers.CharField(source="get_status_anterior_display", read_only=True)
    status_novo_display = serializers.CharField(source="get_status_novo_display", read_only=True)

    class Meta:
        model = ClienteHistorico
        fields = (
            "id", "status_anterior", "status_anterior_display",
            "status_novo", "status_novo_display",
            "usuario", "usuario_nome", "observacao", "criado_em",
        )
        read_only_fields = ("id", "criado_em")


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
    parceiro_nome = serializers.CharField(source="parceiro.nome_entidade", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    produto_display = serializers.CharField(source="get_produto_interesse_display", read_only=True)
    historico = ClienteHistoricoSerializer(many=True, read_only=True)
    produtos = ProdutoContratadoSerializer(many=True, read_only=True)

    class Meta:
        model = Cliente
        fields = (
            "id", "parceiro", "parceiro_nome", "operador",
            "nome", "cnpj", "email", "telefone", "endereco", "cep",
            "produto_interesse", "produto_display",
            "status", "status_display", "arquivo",
            "ativo", "criado_em", "atualizado_em",
            "historico", "produtos",
        )
        read_only_fields = ("id", "criado_em", "atualizado_em")

    def validate_nome(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("O nome e obrigatorio.")
        return value.strip()

    def validate_cnpj(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("O CNPJ e obrigatorio.")
        digits = "".join(c for c in value if c.isdigit())
        if len(digits) != 14:
            raise serializers.ValidationError("CNPJ deve conter 14 digitos.")
        return value

    def validate_email(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("O email e obrigatorio.")
        return value

    def validate_telefone(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("O telefone e obrigatorio.")
        return value

    def validate_endereco(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("O endereco e obrigatorio.")
        return value.strip()

    def validate_cep(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("O CEP e obrigatorio.")
        digits = "".join(c for c in value if c.isdigit())
        if len(digits) != 8:
            raise serializers.ValidationError("CEP deve conter 8 digitos.")
        return value

    def validate_produto_interesse(self, value):
        if not value:
            raise serializers.ValidationError("O produto de interesse e obrigatorio.")
        return value


class ClienteListSerializer(serializers.ModelSerializer):
    parceiro_nome = serializers.CharField(source="parceiro.nome_entidade", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    produto_display = serializers.CharField(source="get_produto_interesse_display", read_only=True)

    class Meta:
        model = Cliente
        fields = (
            "id", "parceiro", "parceiro_nome", "operador",
            "nome", "cnpj", "email", "telefone",
            "produto_interesse", "produto_display",
            "status", "status_display",
            "criado_em", "atualizado_em",
        )
        read_only_fields = ("id", "criado_em", "atualizado_em")


class ClienteStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Cliente.Status.choices)
    observacao = serializers.CharField(required=False, default="", allow_blank=True)

    def validate_status(self, value):
        cliente = self.context.get("cliente")
        if cliente and not cliente.pode_transitar_para(value):
            transicoes = Cliente.TRANSICOES_VALIDAS.get(cliente.status, ())
            permitidos = ", ".join(transicoes) if transicoes else "nenhum (status final)"
            raise serializers.ValidationError(
                f"Transicao de '{cliente.status}' para '{value}' nao e permitida. "
                f"Transicoes validas: {permitidos}."
            )
        return value


class ClienteCreateParceiroSerializer(ClienteSerializer):
    """Herda validacoes do ClienteSerializer. Parceiro nao envia parceiro/operador/status."""

    class Meta:
        model = Cliente
        fields = ("id", "nome", "cnpj", "email", "telefone", "endereco", "cep", "produto_interesse", "arquivo", "status", "criado_em")
        read_only_fields = ("id", "status", "criado_em")
