from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    # Auth
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard-alt"),
    # Leads
    path("leads/", views.LeadListView.as_view(), name="leads"),
    path("leads/novo/", views.LeadCreateView.as_view(), name="lead-create"),
    path("leads/pipeline/", views.LeadPipelineView.as_view(), name="lead-pipeline"),
    path("leads/calendario/", views.LeadCalendarioView.as_view(), name="lead-calendario"),
    path("leads/<int:pk>/", views.LeadDetailView.as_view(), name="lead-detail"),
    path("leads/<int:pk>/status/", views.LeadUpdateStatusView.as_view(), name="lead-update-status"),
    # Clientes
    path("clientes/", views.ClienteListView.as_view(), name="clientes"),
    path("clientes/<int:pk>/", views.ClienteDetailView.as_view(), name="cliente-detail"),
    # Comissões
    path("comissoes/", views.ComissaoListView.as_view(), name="comissoes"),
]
