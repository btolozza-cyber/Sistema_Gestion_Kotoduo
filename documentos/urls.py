from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentoViewSet,
    documentos_lista,
    documento_subir,
    documento_detalle,
    documento_descargar,
    documento_eliminar
)


app_name = "documentos"

router = DefaultRouter()

router.register(
    "documentos",
    DocumentoViewSet,
    basename="documento"
)

urlpatterns = [
    # API REST
    path("api/", include(router.urls)),

    # Interfaz web
    path("", documentos_lista, name="lista"),
    path("subir/", documento_subir, name="subir"),
    path("<int:pk>/", documento_detalle, name="detalle"),
    path("<int:pk>/descargar/", documento_descargar, name="descargar"),
    path("<int:pk>/eliminar/", documento_eliminar, name="eliminar"),
]
