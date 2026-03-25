from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ComissaoViewSet

router = DefaultRouter()
router.register("", ComissaoViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
