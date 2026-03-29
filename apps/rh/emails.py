"""Servico de envio de emails do modulo RH."""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def enviar_acesso_criado(colaborador, username, senha_temporaria):
    """Envia email ao colaborador com dados de acesso ao sistema."""
    contexto = {
        "colaborador": colaborador,
        "username": username,
        "senha": senha_temporaria,
        "url_login": settings.LOGIN_URL,
    }
    assunto = "RUCH — Seu acesso ao sistema foi criado"
    corpo_html = render_to_string("rh/emails/acesso_criado.html", contexto)
    corpo_texto = (
        f"Ola {colaborador.nome_completo},\n\n"
        f"Seu acesso ao sistema Prometheus foi criado.\n\n"
        f"Usuario: {username}\n"
        f"Senha temporaria: {senha_temporaria}\n\n"
        f"Acesse o sistema e altere sua senha no primeiro login.\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    send_mail(
        subject=assunto,
        message=corpo_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[colaborador.email_pessoal],
        html_message=corpo_html,
        fail_silently=True,
    )


def enviar_ausencia_aprovada(ausencia):
    """Notifica colaborador que sua ausencia foi aprovada."""
    colab = ausencia.colaborador
    if not colab.email_pessoal:
        return
    contexto = {"ausencia": ausencia, "colaborador": colab}
    assunto = f"RUCH — Sua solicitacao de {ausencia.get_tipo_display()} foi aprovada"
    corpo_html = render_to_string("rh/emails/ausencia_aprovada.html", contexto)
    corpo_texto = (
        f"Ola {colab.nome_completo},\n\n"
        f"Sua solicitacao de {ausencia.get_tipo_display()} "
        f"({ausencia.data_inicio:%d/%m/%Y} a {ausencia.data_fim:%d/%m/%Y}) "
        f"foi aprovada.\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    send_mail(
        subject=assunto,
        message=corpo_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[colab.email_pessoal],
        html_message=corpo_html,
        fail_silently=True,
    )


def enviar_ausencia_rejeitada(ausencia):
    """Notifica colaborador que sua ausencia foi rejeitada."""
    colab = ausencia.colaborador
    if not colab.email_pessoal:
        return
    contexto = {"ausencia": ausencia, "colaborador": colab}
    assunto = f"RUCH — Sua solicitacao de {ausencia.get_tipo_display()} foi rejeitada"
    corpo_html = render_to_string("rh/emails/ausencia_rejeitada.html", contexto)
    corpo_texto = (
        f"Ola {colab.nome_completo},\n\n"
        f"Sua solicitacao de {ausencia.get_tipo_display()} "
        f"({ausencia.data_inicio:%d/%m/%Y} a {ausencia.data_fim:%d/%m/%Y}) "
        f"foi rejeitada.\n\n"
        f"Motivo: {ausencia.justificativa_rejeicao or 'Nao informado'}\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    send_mail(
        subject=assunto,
        message=corpo_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[colab.email_pessoal],
        html_message=corpo_html,
        fail_silently=True,
    )


def enviar_pesquisa_enps_ativa(pesquisa, colaboradores_emails):
    """Envia email para todos os colaboradores sobre nova pesquisa eNPS."""
    assunto = f"RUCH — Nova pesquisa eNPS: {pesquisa.titulo}"
    corpo_texto = (
        f"Uma nova pesquisa de satisfacao foi aberta.\n\n"
        f"Titulo: {pesquisa.titulo}\n"
        f"Responda ate: {pesquisa.data_encerramento:%d/%m/%Y}\n\n"
        f"Sua opiniao e muito importante para a RUCH.\n"
        f"Acesse o sistema para responder.\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    for email in colaboradores_emails:
        send_mail(
            subject=assunto,
            message=corpo_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )


def _get_emails_rh():
    """Retorna emails do grupo RH."""
    from django.contrib.auth.models import Group
    from apps.accounts.models import Usuario
    emails = set()
    for u in Usuario.objects.filter(is_superuser=True, is_active=True).exclude(email=""):
        emails.add(u.email)
    try:
        grupo = Group.objects.get(name="RH / Pessoas")
        for u in grupo.user_set.filter(is_active=True).exclude(email=""):
            emails.add(u.email)
    except Group.DoesNotExist:
        pass
    return list(emails)


def _enviar_evento_rh(titulo, mensagem, detalhes=None):
    """Envia email generico de evento RH para o grupo RH."""
    try:
        html = render_to_string("rh/emails/colaborador_evento.html", {
            "titulo": titulo,
            "mensagem": mensagem,
            "detalhes": detalhes or {},
        })
        send_mail(
            subject=f"RUCH — {titulo}",
            message=mensagem,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=_get_emails_rh(),
            html_message=html,
            fail_silently=True,
        )
    except Exception:
        pass


def enviar_colaborador_admitido(colaborador):
    """Email para RH quando novo colaborador e cadastrado."""
    _enviar_evento_rh(
        f"Novo colaborador: {colaborador.nome_completo}",
        f"Um novo colaborador foi cadastrado no sistema.",
        {"Nome": colaborador.nome_completo, "Cargo": str(colaborador.cargo), "Departamento": str(colaborador.departamento)},
    )


def enviar_colaborador_desligado(colaborador):
    """Email para RH quando colaborador e desligado."""
    _enviar_evento_rh(
        f"Colaborador desligado: {colaborador.nome_completo}",
        f"O colaborador foi desligado do quadro de funcionarios.",
        {"Nome": colaborador.nome_completo, "Cargo": str(colaborador.cargo), "Departamento": str(colaborador.departamento)},
    )


def enviar_ausencia_solicitada(ausencia):
    """Email para RH quando ausencia e solicitada (antes da aprovacao)."""
    colab = ausencia.colaborador
    _enviar_evento_rh(
        f"Ausencia solicitada: {colab.nome_completo}",
        f"Uma nova solicitacao de ausencia precisa de aprovacao.",
        {
            "Colaborador": colab.nome_completo,
            "Tipo": ausencia.get_tipo_display(),
            "Periodo": f"{ausencia.data_inicio:%d/%m/%Y} a {ausencia.data_fim:%d/%m/%Y}",
            "Dias": str(ausencia.total_dias),
        },
    )


def enviar_treinamento_concluido(participacao):
    """Email para colaborador quando conclui treinamento."""
    colab = participacao.colaborador
    if not colab.email_pessoal:
        return
    _enviar_evento_rh_para_colaborador(
        colab,
        f"Treinamento concluido: {participacao.treinamento.nome}",
        f"Parabens! Voce concluiu o treinamento com sucesso.",
        {"Treinamento": participacao.treinamento.nome, "Status": "Concluido"},
    )


def _enviar_evento_rh_para_colaborador(colaborador, titulo, mensagem, detalhes=None):
    """Envia email de evento RH para um colaborador especifico."""
    if not colaborador.email_pessoal:
        return
    try:
        html = render_to_string("rh/emails/colaborador_evento.html", {
            "titulo": titulo,
            "mensagem": mensagem,
            "detalhes": detalhes or {},
        })
        send_mail(
            subject=f"RUCH — {titulo}",
            message=mensagem,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[colaborador.email_pessoal],
            html_message=html,
            fail_silently=True,
        )
    except Exception:
        pass


def enviar_documento_vencendo(documento):
    """Envia email ao colaborador sobre documento proximo do vencimento."""
    colab = documento.colaborador
    if not colab.email_pessoal:
        return
    from django.utils import timezone
    dias = (documento.data_vencimento - timezone.now().date()).days
    assunto = f"RUCH — Documento a vencer: {documento.nome}"
    corpo_texto = (
        f"Ola {colab.nome_completo},\n\n"
        f"Seu documento '{documento.nome}' vence em {dias} dia(s) "
        f"({documento.data_vencimento:%d/%m/%Y}).\n\n"
        f"Entre em contato com o RH para providenciar a renovacao.\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    send_mail(
        subject=assunto,
        message=corpo_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[colab.email_pessoal],
        fail_silently=True,
    )
