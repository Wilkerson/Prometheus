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
    # Comissoes
    path("comissoes/", views.ComissaoListView.as_view(), name="comissoes"),
    path("comissoes/<int:pk>/pagar/", views.ComissaoMarcarPagoView.as_view(), name="comissao-pagar"),
    # Usuarios
    path("usuarios/", views.UsuarioListView.as_view(), name="usuarios"),
    path("usuarios/novo/", views.UsuarioCreateView.as_view(), name="usuario-create"),
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
    # Avatar
    path("perfil/avatar/", views.AvatarUpdateView.as_view(), name="avatar-update"),
    path("perfil/avatar/remover/", views.AvatarRemoveView.as_view(), name="avatar-remove"),
    # Grupos e permissoes
    path("grupos/", views.GrupoListView.as_view(), name="grupos"),
    path("grupos/novo/", views.GrupoCreateView.as_view(), name="grupo-create"),
    path("grupos/<int:pk>/editar/", views.GrupoUpdateView.as_view(), name="grupo-edit"),
    path("grupos/<int:pk>/excluir/", views.GrupoDeleteView.as_view(), name="grupo-delete"),
]
