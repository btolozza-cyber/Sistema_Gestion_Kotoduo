from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TipoOrdenViewSet,
    OrdenTrabajoViewSet,
    ordenes_lista,
    orden_crear,
    orden_detalle,
    orden_iniciar_produccion,
    orden_cancelar,
    orden_eliminar,
)

app_name = "ordenes"

router = DefaultRouter()

router.register(
    "tipos",
    TipoOrdenViewSet,
    basename="tipo-orden"
)

router.register(
    "ordenes",
    OrdenTrabajoViewSet,
    basename="orden-trabajo"
)

urlpatterns = [
    path("", ordenes_lista, name="lista"),
    path("nueva/", orden_crear, name="crear"),

    path(
        "<int:pk>/iniciar-produccion/",
        orden_iniciar_produccion,
        name="iniciar-produccion"
    ),

    path(
        "<int:pk>/cancelar/",
        orden_cancelar,
        name="cancelar"
    ),

    path(
        "<int:pk>/eliminar/",
        orden_eliminar,
        name="eliminar"
    ),

    path("<int:pk>/", orden_detalle, name="detalle"),

    path("api/", include(router.urls)),
]