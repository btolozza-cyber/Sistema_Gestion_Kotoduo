
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PlantillaProcesoViewSet,
    PlantillaEtapaViewSet,
    PlantillaActividadViewSet
)

router = DefaultRouter()

router.register(
    "procesos",
    PlantillaProcesoViewSet,
    basename="plantilla-proceso"
)

router.register(
    "etapas",
    PlantillaEtapaViewSet,
    basename="plantilla-etapa"
)

router.register(
    "actividades",
    PlantillaActividadViewSet,
    basename="plantilla-actividad"
)

urlpatterns = [
    path("api/", include(router.urls)),
]
