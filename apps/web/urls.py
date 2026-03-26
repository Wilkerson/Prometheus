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
    # Comissoes
    path("comissoes/", views.ComissaoListView.as_view(), name="comissoes"),
]
