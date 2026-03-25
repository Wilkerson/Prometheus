from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.crm.urls")),
    path("api/v1/parceiro/", include("apps.crm.urls_parceiro")),
    path("api/v1/comissoes/", include("apps.comissoes.urls")),
    path("api/v1/integracao/", include("apps.integracao.urls")),
    # Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Web (templates)
    path("", include("apps.web.urls")),
]
