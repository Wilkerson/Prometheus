from django.urls import path

from .views import ClienteIntegracaoCreateView, LeadCallbackView

urlpatterns = [
    path("cliente/", ClienteIntegracaoCreateView.as_view(), name="integracao-cliente"),
    path("lead/status/", LeadCallbackView.as_view(), name="integracao-lead-callback"),
]
