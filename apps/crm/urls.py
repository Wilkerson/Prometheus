from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CalendarioClientesView,
    ClienteViewSet,
    EntidadeParceiraViewSet,
    ProdutoContratadoViewSet,
    SLAClientesView,
)

router = DefaultRouter()
router.register("parceiros", EntidadeParceiraViewSet)
router.register("clientes", ClienteViewSet, basename="cliente")
router.register("produtos-contratados", ProdutoContratadoViewSet)

urlpatterns = [
    path("clientes/calendario/", CalendarioClientesView.as_view(), name="clientes-calendario"),
    path("clientes/sla/", SLAClientesView.as_view(), name="clientes-sla"),
    path("", include(router.urls)),
]
