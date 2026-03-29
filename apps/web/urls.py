from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    # Pagina publica
    path("", views.HomeView.as_view(), name="home"),
    # Auth
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    # Dashboard
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    # Clientes
    path("clientes/", views.ClienteListView.as_view(), name="clientes"),
    path("clientes/novo/", views.ClienteCreateView.as_view(), name="cliente-create"),
    path("clientes/pipeline/", views.ClientePipelineView.as_view(), name="cliente-pipeline"),
    path("clientes/calendario/", views.ClienteCalendarioView.as_view(), name="cliente-calendario"),
    path("clientes/<int:pk>/", views.ClienteDetailView.as_view(), name="cliente-detail"),
    path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente-edit"),
    path("clientes/<int:pk>/status/", views.ClienteUpdateStatusView.as_view(), name="cliente-update-status"),
    path("clientes/<int:pk>/excluir/", views.ClienteDeleteView.as_view(), name="cliente-delete"),
    # Produtos
    path("produtos/", views.ProdutoListView.as_view(), name="produtos"),
    path("produtos/novo/", views.ProdutoCreateView.as_view(), name="produto-create"),
    path("produtos/<int:pk>/editar/", views.ProdutoUpdateView.as_view(), name="produto-edit"),
    path("produtos/<int:pk>/excluir/", views.ProdutoDeleteView.as_view(), name="produto-delete"),
    # Planos
    path("planos/", views.PlanoListView.as_view(), name="planos"),
    path("planos/novo/", views.PlanoCreateView.as_view(), name="plano-create"),
    path("planos/<int:pk>/", views.PlanoDetailView.as_view(), name="plano-detail"),
    path("planos/<int:pk>/editar/", views.PlanoUpdateView.as_view(), name="plano-edit"),
    path("planos/<int:pk>/excluir/", views.PlanoDeleteView.as_view(), name="plano-delete"),
    # Usuarios
    path("usuarios/", views.UsuarioListView.as_view(), name="usuarios"),
    path("usuarios/novo/", views.UsuarioCreateView.as_view(), name="usuario-create"),
    path("usuarios/permissoes-grupo/", views.UsuarioPermissoesGroupView.as_view(), name="usuario-permissoes-grupo"),
    path("usuarios/<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="usuario-edit"),
    path("usuarios/<int:pk>/excluir/", views.UsuarioDeleteView.as_view(), name="usuario-delete"),
    # Entidades Parceiras
    path("parceiros/", views.ParceiroListView.as_view(), name="parceiros"),
    path("parceiros/novo/", views.ParceiroCreateView.as_view(), name="parceiro-create"),
    path("parceiros/<int:pk>/editar/", views.ParceiroUpdateView.as_view(), name="parceiro-edit"),
    path("parceiros/<int:pk>/excluir/", views.ParceiroDeleteView.as_view(), name="parceiro-delete"),
    # Tokens de integracao
    path("tokens/", views.TokenListView.as_view(), name="tokens"),
    path("tokens/novo/", views.TokenCreateView.as_view(), name="token-create"),
    path("tokens/<int:pk>/excluir/", views.TokenDeleteView.as_view(), name="token-delete"),
    # Notificacoes
    path("notificacoes/", views.NotificacaoListView.as_view(), name="notificacoes"),
    path("notificacoes/<int:pk>/ler/", views.NotificacaoLerView.as_view(), name="notificacao-ler"),
    path("notificacoes/ler-todas/", views.NotificacaoLerTodasView.as_view(), name="notificacao-ler-todas"),
    path("notificacoes/painel/", views.NotificacaoPainelView.as_view(), name="notificacao-painel"),
    path("notificacoes/preferencias/", views.NotificacaoPreferenciasView.as_view(), name="notificacao-preferencias"),
    # Grupos e permissoes
    path("grupos/", views.GrupoListView.as_view(), name="grupos"),
    path("grupos/novo/", views.GrupoCreateView.as_view(), name="grupo-create"),
    path("grupos/<int:pk>/editar/", views.GrupoUpdateView.as_view(), name="grupo-edit"),
    path("grupos/<int:pk>/excluir/", views.GrupoDeleteView.as_view(), name="grupo-delete"),
    # RH — Setores
    path("rh/setores/", views.SetorListView.as_view(), name="rh-setores"),
    path("rh/setores/novo/", views.SetorCreateView.as_view(), name="rh-setor-create"),
    path("rh/setores/<int:pk>/editar/", views.SetorUpdateView.as_view(), name="rh-setor-edit"),
    path("rh/setores/<int:pk>/excluir/", views.SetorDeleteView.as_view(), name="rh-setor-delete"),
    # RH — Cargos
    path("rh/cargos/", views.CargoListView.as_view(), name="rh-cargos"),
    path("rh/cargos/novo/", views.CargoCreateView.as_view(), name="rh-cargo-create"),
    path("rh/cargos/<int:pk>/", views.CargoDetailView.as_view(), name="rh-cargo-detail"),
    path("rh/cargos/<int:pk>/editar/", views.CargoUpdateView.as_view(), name="rh-cargo-edit"),
    path("rh/cargos/<int:pk>/excluir/", views.CargoDeleteView.as_view(), name="rh-cargo-delete"),
    # RH — Colaboradores
    path("rh/colaboradores/", views.ColaboradorListView.as_view(), name="rh-colaboradores"),
    path("rh/colaboradores/novo/", views.ColaboradorCreateView.as_view(), name="rh-colaborador-create"),
    path("rh/colaboradores/<int:pk>/", views.ColaboradorDetailView.as_view(), name="rh-colaborador-detail"),
    path("rh/colaboradores/<int:pk>/editar/", views.ColaboradorUpdateView.as_view(), name="rh-colaborador-edit"),
    path("rh/colaboradores/<int:pk>/excluir/", views.ColaboradorDeleteView.as_view(), name="rh-colaborador-delete"),
    path("rh/colaboradores/<int:pk>/foto/", views.ColaboradorFotoView.as_view(), name="rh-colaborador-foto"),
    path("rh/colaboradores/<int:pk>/foto/remover/", views.ColaboradorFotoRemoverView.as_view(), name="rh-colaborador-foto-remover"),
    path("rh/colaboradores/<int:pk>/criar-acesso/", views.ColaboradorCriarAcessoView.as_view(), name="rh-colaborador-criar-acesso"),
    path("rh/colaboradores/<int:pk>/revogar-acesso/", views.ColaboradorRevogarAcessoView.as_view(), name="rh-colaborador-revogar-acesso"),
    # RH — Documentos
    path("rh/documentos/", views.DocumentoListView.as_view(), name="rh-documentos"),
    path("rh/documentos/novo/", views.DocumentoCreateView.as_view(), name="rh-documento-create"),
    path("rh/documentos/<int:pk>/excluir/", views.DocumentoDeleteView.as_view(), name="rh-documento-delete"),
    # RH — Onboarding Templates
    path("rh/onboarding/templates/", views.OnboardingTemplateListView.as_view(), name="rh-onboarding-templates"),
    path("rh/onboarding/templates/novo/", views.OnboardingTemplateCreateView.as_view(), name="rh-onboarding-template-create"),
    path("rh/onboarding/templates/<int:pk>/editar/", views.OnboardingTemplateEditView.as_view(), name="rh-onboarding-template-edit"),
    path("rh/onboarding/templates/<int:pk>/excluir/", views.OnboardingTemplateDeleteView.as_view(), name="rh-onboarding-template-delete"),
    # RH — Onboarding do Colaborador
    path("rh/onboarding/iniciar/<int:colab_pk>/", views.OnboardingIniciarView.as_view(), name="rh-onboarding-iniciar"),
    path("rh/onboarding/<int:pk>/", views.OnboardingDetailView.as_view(), name="rh-onboarding-detail"),
    path("rh/onboarding/item/<int:item_pk>/toggle/", views.OnboardingToggleItemView.as_view(), name="rh-onboarding-toggle-item"),
    # RH — Ausencias
    path("rh/ausencias/", views.AusenciaListView.as_view(), name="rh-ausencias"),
    path("rh/ausencias/novo/", views.AusenciaCreateView.as_view(), name="rh-ausencia-create"),
    path("rh/ausencias/<int:pk>/acao/", views.AusenciaAprovarView.as_view(), name="rh-ausencia-acao"),
    path("rh/ausencias/calendario/", views.AusenciaCalendarioView.as_view(), name="rh-ausencia-calendario"),
    # RH — Treinamentos
    path("rh/treinamentos/", views.TreinamentoListView.as_view(), name="rh-treinamentos"),
    path("rh/treinamentos/novo/", views.TreinamentoCreateView.as_view(), name="rh-treinamento-create"),
    path("rh/treinamentos/<int:pk>/", views.TreinamentoDetailView.as_view(), name="rh-treinamento-detail"),
    path("rh/treinamentos/<int:pk>/editar/", views.TreinamentoUpdateView.as_view(), name="rh-treinamento-edit"),
    path("rh/treinamentos/<int:pk>/excluir/", views.TreinamentoDeleteView.as_view(), name="rh-treinamento-delete"),
    path("rh/treinamentos/<int:treinamento_pk>/inscrever/", views.ParticipacaoCreateView.as_view(), name="rh-participacao-create"),
    path("rh/treinamentos/participacao/<int:pk>/", views.ParticipacaoUpdateView.as_view(), name="rh-participacao-update"),
    # RH — Ciclos e Metas
    path("rh/metas/", views.CicloListView.as_view(), name="rh-ciclos"),
    path("rh/metas/novo/", views.CicloCreateView.as_view(), name="rh-ciclo-create"),
    path("rh/metas/<int:pk>/", views.CicloDetailView.as_view(), name="rh-ciclo-detail"),
    path("rh/metas/<int:ciclo_pk>/nova-meta/", views.MetaCreateView.as_view(), name="rh-meta-create"),
    path("rh/metas/meta/<int:pk>/", views.MetaUpdateView.as_view(), name="rh-meta-update"),
    # RH — PDI
    path("rh/pdi/", views.PDIListView.as_view(), name="rh-pdis"),
    path("rh/pdi/novo/", views.PDICreateView.as_view(), name="rh-pdi-create"),
    path("rh/pdi/<int:pk>/", views.PDIDetailView.as_view(), name="rh-pdi-detail"),
    path("rh/pdi/<int:pdi_pk>/nova-acao/", views.AcaoPDICreateView.as_view(), name="rh-acao-pdi-create"),
    path("rh/pdi/acao/<int:pk>/", views.AcaoPDIUpdateView.as_view(), name="rh-acao-pdi-update"),
    # RH — eNPS
    path("rh/enps/", views.ENPSListView.as_view(), name="rh-enps"),
    path("rh/enps/novo/", views.ENPSCreateView.as_view(), name="rh-enps-create"),
    path("rh/enps/<int:pk>/", views.ENPSDetailView.as_view(), name="rh-enps-detail"),
    path("rh/enps/<int:pk>/responder/", views.ENPSResponderView.as_view(), name="rh-enps-responder"),
    path("rh/enps/<int:pk>/status/", views.ENPSStatusView.as_view(), name="rh-enps-status"),
    # RH — Relatorios
    path("rh/relatorios/", views.RelatoriosRHView.as_view(), name="rh-relatorios"),
    # Financeiro — Lancamentos
    path("financeiro/lancamentos/", views.LancamentoListView.as_view(), name="fin-lancamentos"),
    path("financeiro/lancamentos/novo/", views.LancamentoCreateView.as_view(), name="fin-lancamento-create"),
    path("financeiro/lancamentos/<int:pk>/", views.LancamentoDetailView.as_view(), name="fin-lancamento-detail"),
    path("financeiro/lancamentos/<int:pk>/status/", views.LancamentoStatusView.as_view(), name="fin-lancamento-status"),
    # Financeiro — Contas Bancarias
    path("financeiro/contas/", views.ContaListView.as_view(), name="fin-contas"),
    path("financeiro/contas/novo/", views.ContaCreateView.as_view(), name="fin-conta-create"),
    # Financeiro — Cobrancas
    path("financeiro/cobrancas/", views.CobrancaListView.as_view(), name="fin-cobrancas"),
    path("financeiro/cobrancas/novo/", views.CobrancaCreateView.as_view(), name="fin-cobranca-create"),
    path("financeiro/cobrancas/<int:pk>/confirmar/", views.CobrancaConfirmarView.as_view(), name="fin-cobranca-confirmar"),
    # Financeiro — Despesas
    path("financeiro/despesas/", views.DespesaListView.as_view(), name="fin-despesas"),
    path("financeiro/despesas/novo/", views.DespesaCreateView.as_view(), name="fin-despesa-create"),
    path("financeiro/despesas/<int:pk>/confirmar/", views.DespesaConfirmarView.as_view(), name="fin-despesa-confirmar"),
    # Financeiro — Notas Fiscais
    path("financeiro/nfs/", views.NotaFiscalListView.as_view(), name="fin-nfs"),
    path("financeiro/nfs/novo/", views.NotaFiscalCreateView.as_view(), name="fin-nf-create"),
    # Financeiro — Folha de Pagamento
    path("financeiro/folha/", views.FolhaListView.as_view(), name="fin-folha"),
    path("financeiro/folha/colaboradores/", views.FolhaColaboradoresView.as_view(), name="fin-folha-colaboradores"),
    path("financeiro/folha/novo/", views.FolhaCreateView.as_view(), name="fin-folha-create"),
    path("financeiro/folha/<int:pk>/editar/", views.FolhaEditView.as_view(), name="fin-folha-edit"),
    path("financeiro/folha/<int:pk>/excluir/", views.FolhaDeleteView.as_view(), name="fin-folha-delete"),
    path("financeiro/folha/<int:pk>/confirmar/", views.FolhaConfirmarView.as_view(), name="fin-folha-confirmar"),
    path("financeiro/folha/configuracao/", views.ConfiguracaoFolhaView.as_view(), name="fin-folha-config"),
    path("financeiro/folha/gerar/", views.GerarFolhaView.as_view(), name="fin-folha-gerar"),
    path("financeiro/folha/aprovar-todos/", views.FolhaAprovarTodosView.as_view(), name="fin-folha-aprovar-todos"),
    path("financeiro/folha/exportar/", views.FolhaExportarView.as_view(), name="fin-folha-exportar"),
    # Financeiro — Tributos
    path("financeiro/tributos/", views.TributoListView.as_view(), name="fin-tributos"),
    path("financeiro/tributos/novo/", views.TributoCreateView.as_view(), name="fin-tributo-create"),
    path("financeiro/tributos/<int:pk>/confirmar/", views.TributoConfirmarView.as_view(), name="fin-tributo-confirmar"),
    # Financeiro — Ativos (Patrimonio)
    path("financeiro/ativos/", views.AtivoListView.as_view(), name="fin-ativos"),
    path("financeiro/ativos/novo/", views.AtivoCreateView.as_view(), name="fin-ativo-create"),
    path("financeiro/ativos/<int:pk>/", views.AtivoDetailView.as_view(), name="fin-ativo-detail"),
    path("financeiro/ativos/<int:pk>/editar/", views.AtivoEditView.as_view(), name="fin-ativo-edit"),
    path("financeiro/ativos/<int:pk>/baixa/", views.AtivoBaixaView.as_view(), name="fin-ativo-baixa"),
    # Financeiro — Relatorios
    path("financeiro/dashboard/", views.DashboardFinanceiroView.as_view(), name="fin-dashboard"),
    path("financeiro/dre/", views.DREView.as_view(), name="fin-dre"),
    path("financeiro/fluxo-caixa/", views.FluxoCaixaView.as_view(), name="fin-fluxo-caixa"),
    path("financeiro/fechamento/", views.FechamentoMensalView.as_view(), name="fin-fechamento"),
    path("financeiro/fechamento/exportar/", views.FechamentoExportView.as_view(), name="fin-fechamento-exportar"),
    # Financeiro — Asaas (Gateway)
    path("financeiro/asaas/", views.AsaasDashboardView.as_view(), name="fin-asaas"),
    path("financeiro/asaas/clientes/", views.AsaasClienteListView.as_view(), name="fin-asaas-clientes"),
    path("financeiro/asaas/sincronizar/<int:cliente_pk>/", views.AsaasSincronizarClienteView.as_view(), name="fin-asaas-sincronizar"),
    path("financeiro/asaas/cobrancas/", views.AsaasCobrancaListView.as_view(), name="fin-asaas-cobrancas"),
    path("financeiro/asaas/cobrancas/novo/", views.AsaasCriarCobrancaView.as_view(), name="fin-asaas-criar-cobranca"),
    path("financeiro/asaas/cobrancas/<int:pk>/", views.AsaasCobrancaDetailView.as_view(), name="fin-asaas-cobranca-detail"),
    path("financeiro/asaas/cobrancas/<int:pk>/excluir/", views.AsaasCobrancaDeleteView.as_view(), name="fin-asaas-cobranca-delete"),
    path("financeiro/asaas/assinaturas/", views.AsaasAssinaturaListView.as_view(), name="fin-asaas-assinaturas"),
    path("financeiro/asaas/webhook-log/", views.AsaasWebhookLogView.as_view(), name="fin-asaas-webhook-log"),
]
