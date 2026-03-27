from django.db import migrations
from django.utils.text import slugify


DEPARTAMENTOS = [
    {"slug": "comercial", "nome": "Comercial", "ordem": 1},
    {"slug": "financeiro", "nome": "Financeiro", "ordem": 2},
    {"slug": "rh", "nome": "RH / Pessoas", "ordem": 3},
    {"slug": "marketing", "nome": "Marketing", "ordem": 4},
    {"slug": "tecnologia", "nome": "Tecnologia", "ordem": 5},
]


def seed_departamentos(apps, schema_editor):
    Departamento = apps.get_model("rh", "Departamento")

    # Atualizar departamentos existentes (adicionar slug se nao tem)
    for depto in Departamento.objects.filter(slug=""):
        depto.slug = slugify(depto.nome)
        depto.save(update_fields=["slug"])

    # Criar departamentos do sistema que nao existem
    for d in DEPARTAMENTOS:
        Departamento.objects.get_or_create(
            slug=d["slug"],
            defaults={"nome": d["nome"], "ordem": d["ordem"]},
        )


def reverse_seed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("rh", "0002_departamento_slug_setor"),
    ]

    operations = [
        migrations.RunPython(seed_departamentos, reverse_seed),
    ]
