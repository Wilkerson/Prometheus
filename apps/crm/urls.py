from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClienteViewSet, EntidadeParceiraViewSet, LeadViewSet, ProdutoContratadoViewSet

router = DefaultRouter()
router.register("parceiros", EntidadeParceiraViewSet)
router.register("leads", LeadViewSet, basename="lead")
router.register("clientes", ClienteViewSet)
router.register("produtos-contratados", ProdutoContratadoViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
