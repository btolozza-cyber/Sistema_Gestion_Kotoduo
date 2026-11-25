from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import DocumentoViewSet

router = DefaultRouter()

router.register(
    "documentos",
    DocumentoViewSet,
    basename="documento"
)

urlpatterns = [
    path("api/", include(router.urls)),
]
