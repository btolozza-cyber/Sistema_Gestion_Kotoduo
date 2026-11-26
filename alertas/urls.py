from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    InsumoViewSet,
    AlertaInsumoViewSet,
    MovimientoInsumoViewSet,
    inventario_inicio,
    insumos_lista,
    insumo_crear,
    insumo_editar,
    insumo_detalle,
    movimientos_lista,
    movimiento_crear,
    alerta_actualizar_estado,
)

app_name = "alertas"

router = DefaultRouter()

router.register(
    "insumos",
    InsumoViewSet,
    basename="insumo"
)

router.register(
    "movimientos",
    MovimientoInsumoViewSet,
    basename="movimiento"
)

router.register(
    "alertas",
    AlertaInsumoViewSet,
    basename="alerta"
)

urlpatterns = [
    path("", inventario_inicio, name="inventario"),

    path("insumos/", insumos_lista, name="insumos"),
    path("insumos/nuevo/", insumo_crear, name="insumo-crear"),
    path("insumos/<int:pk>/editar/", insumo_editar, name="insumo-editar"),
    path("insumos/<int:pk>/", insumo_detalle, name="insumo-detalle"),

    path("movimientos/", movimientos_lista, name="movimientos"),
    path("movimientos/nuevo/", movimiento_crear, name="movimiento-crear"),

    path(
        "alertas/<int:pk>/estado/",
        alerta_actualizar_estado,
        name="alerta-estado"
    ),

    path("api/", include(router.urls)),
]