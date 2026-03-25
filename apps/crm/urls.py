from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CalendarioLeadsView,
    ClienteViewSet,
    EntidadeParceiraViewSet,
    LeadViewSet,
    ProdutoContratadoViewSet,
    SLALeadsView,
)

router = DefaultRouter()
router.register("parceiros", EntidadeParceiraViewSet)
router.register("leads", LeadViewSet, basename="lead")
router.register("clientes", ClienteViewSet)
router.register("produtos-contratados", ProdutoContratadoViewSet)

urlpatterns = [
    path("leads/calendario/", CalendarioLeadsView.as_view(), name="leads-calendario"),
    path("leads/sla/", SLALeadsView.as_view(), name="leads-sla"),
    path("", include(router.urls)),
]
