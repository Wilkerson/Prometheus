from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_parceiro import ParceiroDashboardView, ParceiroLeadViewSet

router = DefaultRouter()
router.register("leads", ParceiroLeadViewSet, basename="parceiro-lead")

urlpatterns = [
    path("dashboard/", ParceiroDashboardView.as_view(), name="parceiro-dashboard"),
    path("", include(router.urls)),
]
