from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    InsumoViewSet,
    AlertaInsumoViewSet,
    MovimientoInsumoViewSet,
)


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
    path("api/", include(router.urls)),
]
