from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", RedirectView.as_view(url="/login/", permanent=False)),

    path("", include("usuarios.urls")),
    path("ordenes/", include("ordenes.urls")),
    path("produccion/", include("produccion.urls")),
    path("alertas/", include("alertas.urls")),
    path("plantillas/", include("plantillas.urls")),
    path("documentos/", include("documentos.urls")),
    path("auditoria/", include("auditoria.urls")),
]