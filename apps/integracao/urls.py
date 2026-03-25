from django.urls import path

from .views import ClienteIntegracaoCreateView

urlpatterns = [
    path("cliente/", ClienteIntegracaoCreateView.as_view(), name="integracao-cliente"),
]
