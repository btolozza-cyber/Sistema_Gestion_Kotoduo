from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TipoOrdenViewSet,
    OrdenTrabajoViewSet,
    ordenes_lista,
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
    path("api/", include(router.urls)),
]
