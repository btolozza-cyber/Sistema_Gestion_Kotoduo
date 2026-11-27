from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib.auth.views import LogoutView

from .views import (
    IniciarSesionView,
    UsuarioViewSet,
    dashboard,
    usuarios_lista,
    usuario_crear,
    usuario_editar,
    usuario_detalle,
    usuario_cambiar_estado,
)

app_name = "usuarios"

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = [
    path("login/", IniciarSesionView.as_view(), name="login"),
    path("dashboard/", dashboard, name="dashboard"),
    path("logout/", LogoutView.as_view(), name="logout"),

    path("usuarios/", usuarios_lista, name="lista"),
    path("usuarios/crear/", usuario_crear, name="crear"),
    path("usuarios/<int:pk>/", usuario_detalle, name="detalle"),
    path("usuarios/<int:pk>/editar/", usuario_editar, name="editar"),
    path(
        "usuarios/<int:pk>/estado/",
        usuario_cambiar_estado,
        name="cambiar_estado"
    ),

    path("api/", include(router.urls)),
]