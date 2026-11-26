
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AreaProduccionViewSet,
    EtapaProduccionViewSet,
    ActividadViewSet,
    HistorialEtapaViewSet,
    HistorialActividadViewSet,
    produccion_inicio,
    etapas_lista,
    etapa_cambiar_estado,
)

app_name = "produccion"

router = DefaultRouter()
router.register("areas", AreaProduccionViewSet, basename="area")
router.register("etapas", EtapaProduccionViewSet, basename="etapa")
router.register("actividades", ActividadViewSet, basename="actividad")
router.register("historial-etapas", HistorialEtapaViewSet, basename="historial-etapa")
router.register("historial-actividades", HistorialActividadViewSet, basename="historial-actividad")

urlpatterns = [
    path("", produccion_inicio, name="inicio"),
    path("api/", include(router.urls)),
    path("etapas/", etapas_lista, name="etapas"),
    path("etapas/<int:pk>/estado/", etapa_cambiar_estado, name="etapa-estado"),
]
