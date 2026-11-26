
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RegistroAuditoriaViewSet,
    auditoria_lista,
    auditoria_detalle
)


app_name = "auditoria"

router = DefaultRouter()

router.register(
    "registros",
    RegistroAuditoriaViewSet,
    basename="registro-auditoria"
)

urlpatterns = [
    # API REST
    path("api/", include(router.urls)),

    # Interfaz web
    path("", auditoria_lista, name="lista"),
    path("<int:pk>/", auditoria_detalle, name="detalle"),
]
