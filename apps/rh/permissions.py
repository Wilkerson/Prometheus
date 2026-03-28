"""
Sistema de permissoes baseado em departamento + nivel hierarquico.
Atribui permissoes diretas ao usuario com base no cargo do colaborador.
"""

from django.contrib.auth.models import Permission

# Mapa: slug do departamento -> lista de (app_label, model) que o depto gerencia
DEPARTAMENTO_MODELS = {
    "comercial": [
        ("crm", "cliente"),
        ("crm", "produto"),
        ("crm", "plano"),
        ("crm", "planoproduto"),
        ("crm", "entidadeparceira"),
    ],
    "financeiro": [
        ("financeiro", "lancamento"),
        ("financeiro", "contabancaria"),
        ("financeiro", "categoriafinanceira"),
        ("financeiro", "cobranca"),
        ("financeiro", "despesa"),
        ("financeiro", "notafiscal"),
        ("financeiro", "folhapagamento"),
        ("financeiro", "tributo"),
    ],
    "rh": [
        ("rh", "colaborador"),
        ("rh", "cargo"),
        ("rh", "setor"),
        ("rh", "documentocolaborador"),
        ("rh", "onboardingtemplate"),
        ("rh", "onboardingcolaborador"),
        ("rh", "solicitacaoausencia"),
        ("rh", "saldoferias"),
        ("rh", "treinamento"),
        ("rh", "participacaotreinamento"),
        ("rh", "cicloavaliacao"),
        ("rh", "meta"),
        ("rh", "pdi"),
        ("rh", "acaopdi"),
        ("rh", "pesquisaenps"),
        ("rh", "perguntaenps"),
        ("rh", "respostaenps"),
    ],
}

# Niveis hierarquicos ordenados
NIVEIS = ["estagiario", "assistente", "analista", "especialista", "gerente", "diretor"]

# Acoes por nivel
#   view: todos
#   add: assistente+
#   change: analista+
#   delete: especialista+
ACOES_POR_NIVEL = {
    "estagiario": ["view"],
    "assistente": ["view", "add"],
    "analista": ["view", "add", "change"],
    "especialista": ["view", "add", "change", "delete"],
    "gerente": ["view", "add", "change", "delete"],
    "diretor": ["view", "add", "change", "delete"],
}

# Permissoes base que todo colaborador com acesso recebe (self-service)
PERMISSOES_BASE = [
    "rh.view_solicitacaoausencia",
    "rh.add_solicitacaoausencia",
    "rh.view_treinamento",
    "rh.view_participacaotreinamento",
    "rh.view_documentocolaborador",
    "rh.view_onboardingcolaborador",
    "rh.view_saldoferias",
    "rh.view_cicloavaliacao",
    "rh.view_meta",
    "rh.view_pdi",
    "rh.view_pesquisaenps",
    "rh.add_respostaenps",
]


def calcular_permissoes(colaborador):
    """Calcula as permissoes para um colaborador baseado no departamento e nivel.
    Retorna um QuerySet de Permission.
    """
    nivel = colaborador.cargo.nivel if colaborador.cargo else "assistente"
    depto_slug = colaborador.departamento.slug if colaborador.departamento else None

    acoes = ACOES_POR_NIVEL.get(nivel, ["view"])

    # Permissoes base (self-service)
    perm_codenames = []
    for perm_str in PERMISSOES_BASE:
        app, codename = perm_str.split(".")
        perm_codenames.append(codename)

    # Permissoes do departamento
    if depto_slug and depto_slug in DEPARTAMENTO_MODELS:
        models = DEPARTAMENTO_MODELS[depto_slug]
        for app_label, model_name in models:
            for acao in acoes:
                perm_codenames.append(f"{acao}_{model_name}")

    return Permission.objects.filter(codename__in=perm_codenames)


def atribuir_permissoes(colaborador):
    """Atribui permissoes diretas ao usuario vinculado ao colaborador.
    Remove permissoes anteriores e recalcula do zero.
    """
    if not colaborador.usuario or not colaborador.usuario.is_active:
        return

    user = colaborador.usuario
    perms = calcular_permissoes(colaborador)

    # Manter grupo Colaborador + permissoes calculadas
    from django.contrib.auth.models import Group
    grupo_colab = Group.objects.filter(name="Colaborador").first()

    # Limpar permissoes diretas anteriores e reatribuir
    user.user_permissions.set(perms)

    # Garantir grupo Colaborador
    if grupo_colab and not user.groups.filter(pk=grupo_colab.pk).exists():
        user.groups.add(grupo_colab)
