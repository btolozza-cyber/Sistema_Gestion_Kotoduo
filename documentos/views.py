
from django.db import transaction
from django.db.models import Q

from rest_framework import viewsets
from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
    IsAuthenticated
)
from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
    JSONParser
)

from .models import Documento
from .serializers import DocumentoSerializer

from auditoria.services import registrar_evento


def es_gestor_documentos(user):
    return (
        user.is_superuser
        or user.groups.filter(
            name__in=[
                "Administrador",
                "Supervisor de producción"
            ]
        ).exists()
    )


class PermisoDocumento(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if es_gestor_documentos(user):
            return True

        if user.groups.filter(name="Operario").exists():
            return request.method in SAFE_METHODS

        return False


class DocumentoViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentoSerializer
    permission_classes = [
        IsAuthenticated,
        PermisoDocumento
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser
    ]

    queryset = Documento.objects.select_related(
        "orden_trabajo",
        "subido_por"
    )

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if es_gestor_documentos(user):
            return queryset

        if user.groups.filter(name="Operario").exists():
            return queryset.filter(
                Q(
                    orden_trabajo__etapas__responsable=user
                )
                | Q(
                    orden_trabajo__etapas__actividades__responsable=user
                )
            ).distinct()

        return queryset.none()

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user

        documento = serializer.save(
            subido_por=usuario
        )

        registrar_evento(
            usuario=usuario,
            modulo="documentos",
            accion="subida",
            descripcion=(
                f"Subió el documento '{documento.nombre}' "
                f"a la orden '{documento.orden_trabajo.numero}'."
            ),
            objeto_id=documento.id,
            objeto_referencia=documento.orden_trabajo.numero
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        usuario = self.request.user

        registrar_evento(
            usuario=usuario,
            modulo="documentos",
            accion="eliminacion",
            descripcion=(
                f"Eliminó el documento '{instance.nombre}' "
                f"de la orden '{instance.orden_trabajo.numero}'."
            ),
            objeto_id=instance.id,
            objeto_referencia=instance.orden_trabajo.numero
        )

        if instance.archivo:
            instance.archivo.delete(save=False)

        instance.delete()
