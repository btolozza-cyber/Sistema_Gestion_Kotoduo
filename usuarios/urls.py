from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    IniciarSesionView,
    UsuarioViewSet,
    dashboard,
)

app_name = "usuarios"

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = [
    path("login/", IniciarSesionView.as_view(), name="login"),
    path("dashboard/", dashboard, name="dashboard"),
    path("api/", include(router.urls)),
]
