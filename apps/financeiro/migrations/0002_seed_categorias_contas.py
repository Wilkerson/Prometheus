from django.db import migrations


CATEGORIAS = [
    # Receitas
    {"nome": "Receita de servicos", "tipo": "receita", "ordem": 1, "subs": [
        {"nome": "Mensalidade de planos", "ordem": 1},
        {"nome": "Taxa de implantacao", "ordem": 2},
        {"nome": "Projeto avulso", "ordem": 3},
        {"nome": "Consultoria", "ordem": 4},
    ]},
    {"nome": "Receita financeira", "tipo": "receita", "ordem": 2, "subs": [
        {"nome": "Rendimento de conta", "ordem": 1},
    ]},
    # Despesas
    {"nome": "Pessoal", "tipo": "despesa", "ordem": 1, "subs": [
        {"nome": "Pro-labore", "ordem": 1},
        {"nome": "Salarios e encargos", "ordem": 2},
        {"nome": "Comissoes de parceiros", "ordem": 3},
        {"nome": "Bonus e gratificacoes", "ordem": 4},
    ]},
    {"nome": "Operacional", "tipo": "despesa", "ordem": 2, "subs": [
        {"nome": "Ferramentas e SaaS", "ordem": 1},
        {"nome": "Infraestrutura (servidor, dominio)", "ordem": 2},
        {"nome": "Marketing e trafego pago", "ordem": 3},
    ]},
    {"nome": "Administrativo", "tipo": "despesa", "ordem": 3, "subs": [
        {"nome": "Contabilidade", "ordem": 1},
        {"nome": "Juridico", "ordem": 2},
    ]},
    {"nome": "Impostos e taxas", "tipo": "despesa", "ordem": 4, "subs": [
        {"nome": "DAS (Simples Nacional)", "ordem": 1},
        {"nome": "ISS", "ordem": 2},
        {"nome": "Taxas bancarias e IOF", "ordem": 3},
    ]},
]

CONTAS = [
    {"nome": "Conta PJ Principal", "tipo": "corrente", "banco": "A definir"},
    {"nome": "Asaas", "tipo": "pagamento", "banco": "Asaas"},
    {"nome": "Caixa Fisico", "tipo": "caixa", "banco": ""},
]


def seed(apps, schema_editor):
    Categoria = apps.get_model("financeiro", "CategoriaFinanceira")
    Conta = apps.get_model("financeiro", "ContaBancaria")

    for cat in CATEGORIAS:
        pai = Categoria.objects.create(
            nome=cat["nome"], tipo=cat["tipo"], ordem=cat["ordem"],
        )
        for sub in cat.get("subs", []):
            Categoria.objects.create(
                nome=sub["nome"], tipo=cat["tipo"], pai=pai, ordem=sub["ordem"],
            )

    for conta in CONTAS:
        Conta.objects.create(
            nome=conta["nome"], tipo=conta["tipo"], banco=conta.get("banco", ""),
        )


def reverse(apps, schema_editor):
    apps.get_model("financeiro", "CategoriaFinanceira").objects.all().delete()
    apps.get_model("financeiro", "ContaBancaria").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("financeiro", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, reverse),
    ]
