from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AreaProduccionViewSet,
    EtapaProduccionViewSet,
    ActividadViewSet,
    HistorialEtapaViewSet,
    HistorialActividadViewSet,
)

router = DefaultRouter()

router.register("areas", AreaProduccionViewSet, basename="area")
router.register("etapas", EtapaProduccionViewSet, basename="etapa")
router.register("actividades", ActividadViewSet, basename="actividad")
router.register("historial-etapas", HistorialEtapaViewSet, basename="historial-etapa")
router.register("historial-actividades", HistorialActividadViewSet, basename="historial-actividad")

urlpatterns = [
    path("api/", include(router.urls)),
]
