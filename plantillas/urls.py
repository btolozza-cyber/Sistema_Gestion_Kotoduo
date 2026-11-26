from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PlantillaProcesoViewSet,
    PlantillaEtapaViewSet,
    PlantillaActividadViewSet,
)

from .web_views import (
    plantillas_lista,
    plantilla_crear,
    plantilla_detalle,
    plantilla_editar,
    plantilla_cambiar_estado,
    plantilla_etapa_crear,
    plantilla_etapa_editar,
    plantilla_actividad_crear,
    plantilla_actividad_editar,
)


app_name = "plantillas"


# ==========================================================
# API REST
# ==========================================================

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


# ==========================================================
# RUTAS WEB
# ==========================================================

urlpatterns = [
    path("", plantillas_lista, name="lista"),

    path("nueva/", plantilla_crear, name="crear"),

    path("<int:pk>/", plantilla_detalle, name="detalle"),

    path(
        "<int:pk>/editar/",
        plantilla_editar,
        name="editar"
    ),

    path(
        "<int:pk>/estado/",
        plantilla_cambiar_estado,
        name="cambiar-estado"
    ),

    path(
        "<int:plantilla_pk>/etapas/nueva/",
        plantilla_etapa_crear,
        name="etapa-crear"
    ),

    path(
        "etapas/<int:pk>/editar/",
        plantilla_etapa_editar,
        name="etapa-editar"
    ),

    path(
        "etapas/<int:etapa_pk>/actividades/nueva/",
        plantilla_actividad_crear,
        name="actividad-crear"
    ),

    path(
        "actividades/<int:pk>/editar/",
        plantilla_actividad_editar,
        name="actividad-editar"
    ),

    path("api/", include(router.urls)),
]
