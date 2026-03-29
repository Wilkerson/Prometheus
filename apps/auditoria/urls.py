from django.urls import path

from . import views

app_name = "auditoria"

urlpatterns = [
    path("", views.AuditoriaDashboardView.as_view(), name="dashboard"),
    path("exportar/csv/", views.AuditoriaExportCSVView.as_view(), name="export-csv"),
    path("exportar/pdf/", views.AuditoriaExportPDFView.as_view(), name="export-pdf"),
    path("log/<int:pk>/", views.AuditoriaDetailView.as_view(), name="detail"),
    path("<str:departamento>/", views.AuditoriaListView.as_view(), name="list"),
]
