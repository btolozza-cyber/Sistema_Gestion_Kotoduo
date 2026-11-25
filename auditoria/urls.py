from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import RegistroAuditoriaViewSet

router = DefaultRouter()

router.register(
    "registros",
    RegistroAuditoriaViewSet,
    basename="registro-auditoria"
)

urlpatterns = [
    path("api/", include(router.urls)),
]
