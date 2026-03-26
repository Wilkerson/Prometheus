from django.urls import path

from .views import ClienteCallbackView, ClienteIntegracaoCreateView

urlpatterns = [
    path("cliente/", ClienteIntegracaoCreateView.as_view(), name="integracao-cliente"),
    path("cliente/status/", ClienteCallbackView.as_view(), name="integracao-cliente-callback"),
]
