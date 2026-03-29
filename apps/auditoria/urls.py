from django.urls import path

from . import views

app_name = "auditoria"

urlpatterns = [
    path("", views.AuditoriaDashboardView.as_view(), name="dashboard"),
    path("<str:departamento>/", views.AuditoriaListView.as_view(), name="list"),
]
