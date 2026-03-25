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
    # Leads
    path("leads/", views.LeadListView.as_view(), name="leads"),
    path("leads/novo/", views.LeadCreateView.as_view(), name="lead-create"),
    path("leads/pipeline/", views.LeadPipelineView.as_view(), name="lead-pipeline"),
    path("leads/calendario/", views.LeadCalendarioView.as_view(), name="lead-calendario"),
    path("leads/<int:pk>/", views.LeadDetailView.as_view(), name="lead-detail"),
    path("leads/<int:pk>/status/", views.LeadUpdateStatusView.as_view(), name="lead-update-status"),
    # Clientes
    path("clientes/", views.ClienteListView.as_view(), name="clientes"),
    path("clientes/novo/", views.ClienteCreateView.as_view(), name="cliente-create"),
    path("clientes/<int:pk>/", views.ClienteDetailView.as_view(), name="cliente-detail"),
    path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente-edit"),
    path("clientes/<int:pk>/excluir/", views.ClienteDeleteView.as_view(), name="cliente-delete"),
    # Comissões
    path("comissoes/", views.ComissaoListView.as_view(), name="comissoes"),
]
