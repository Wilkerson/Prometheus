from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_parceiro import ParceiroDashboardView, ParceiroClienteViewSet

router = DefaultRouter()
router.register("clientes", ParceiroClienteViewSet, basename="parceiro-cliente")

urlpatterns = [
    path("dashboard/", ParceiroDashboardView.as_view(), name="parceiro-dashboard"),
    path("", include(router.urls)),
]
