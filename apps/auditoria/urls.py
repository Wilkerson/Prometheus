from django.urls import path

from . import views

app_name = "auditoria"

urlpatterns = [
    path("", views.AuditoriaDashboardView.as_view(), name="dashboard"),
    path("exportar/", views.AuditoriaExportView.as_view(), name="export"),
    path("log/<int:pk>/", views.AuditoriaDetailView.as_view(), name="detail"),
    path("<str:departamento>/", views.AuditoriaListView.as_view(), name="list"),
]
