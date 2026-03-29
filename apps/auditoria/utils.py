"""
Utilitario central para registrar eventos de auditoria.
Usado por views, signals, tasks e webhooks.
"""

from django.contrib.contenttypes.models import ContentType


def registrar(
    acao,
    departamento,
    descricao,
    instance=None,
    usuario=None,
    request=None,
    detalhes=None,
    fonte="interno",
):
    """Cria um registro no AuditLog.

    Args:
        acao: criacao|edicao|exclusao|status|exportacao|webhook|sistema
        departamento: financeiro|comercial|rh|administracao|integracao|sistema
        descricao: texto legivel do evento
        instance: objeto Django afetado (opcional)
        usuario: User que executou (opcional, extraido de request se nao informado)
        request: HttpRequest (opcional, para extrair usuario)
        detalhes: dict com dados extras (diffs, payloads, etc)
        fonte: interno|asaas_webhook|api|celery|sistema
    """
    from apps.auditoria.models import AuditLog

    if usuario is None and request is not None:
        usuario = request.user if request.user.is_authenticated else None

    ct = None
    obj_id = None
    obj_repr = ""
    if instance is not None:
        try:
            ct = ContentType.objects.get_for_model(instance)
            obj_id = instance.pk
            obj_repr = str(instance)[:300]
        except Exception:
            pass

    AuditLog.objects.create(
        acao=acao,
        departamento=departamento,
        descricao=descricao[:500],
        detalhes=detalhes or {},
        content_type=ct,
        object_id=obj_id,
        object_repr=obj_repr,
        usuario=usuario,
        fonte=fonte,
    )
