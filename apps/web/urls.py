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
]
