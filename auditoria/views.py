from rest_framework import viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import RegistroAuditoria
from .serializers import RegistroAuditoriaSerializer


class PuedeConsultarAuditoria(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return (
            user.is_superuser
            or user.groups.filter(
                name__in=[
                    "Administrador",
                    "Supervisor de producción"
                ]
            ).exists()
        )


class RegistroAuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RegistroAuditoriaSerializer
    permission_classes = [
        IsAuthenticated,
        PuedeConsultarAuditoria
    ]

    queryset = RegistroAuditoria.objects.select_related(
        "usuario"
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        usuario = params.get("usuario")
        modulo = params.get("modulo")
        accion = params.get("accion")
        fecha_desde = params.get("fecha_desde")
        fecha_hasta = params.get("fecha_hasta")

        if usuario:
            queryset = queryset.filter(usuario_id=usuario)

        if modulo:
            queryset = queryset.filter(modulo=modulo)

        if accion:
            queryset = queryset.filter(accion=accion)

        if fecha_desde:
            queryset = queryset.filter(fecha__date__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha__date__lte=fecha_hasta)

        return queryset
