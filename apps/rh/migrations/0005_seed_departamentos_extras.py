from django.db import migrations


NOVOS_DEPARTAMENTOS = [
    {"slug": "juridico", "nome": "Juridico", "ordem": 6},
    {"slug": "operacoes", "nome": "Operacoes", "ordem": 7},
    {"slug": "produto", "nome": "Produto", "ordem": 8},
]


def seed(apps, schema_editor):
    Departamento = apps.get_model("rh", "Departamento")
    for d in NOVOS_DEPARTAMENTOS:
        Departamento.objects.get_or_create(
            slug=d["slug"],
            defaults={"nome": d["nome"], "ordem": d["ordem"]},
        )


def reverse(apps, schema_editor):
    Departamento = apps.get_model("rh", "Departamento")
    Departamento.objects.filter(slug__in=["juridico", "operacoes", "produto"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rh", "0004_remove_slug_default"),
    ]

    operations = [
        migrations.RunPython(seed, reverse),
    ]
