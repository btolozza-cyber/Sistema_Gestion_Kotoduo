
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator

from rest_framework import viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import RegistroAuditoria
from .serializers import RegistroAuditoriaSerializer


# PERMISOS

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


def verificar_acceso_auditoria(user):
    if not (
        user.is_superuser
        or user.groups.filter(
            name__in=[
                "Administrador",
                "Supervisor de producción"
            ]
        ).exists()
    ):
        raise PermissionDenied


# API REST

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


# INTERFAZ WEB

@login_required
def auditoria_lista(request):
    verificar_acceso_auditoria(request.user)

    registros = RegistroAuditoria.objects.select_related(
        "usuario"
    ).all()

    # FILTROS

    usuario = request.GET.get("usuario", "")
    modulo = request.GET.get("modulo", "")
    accion = request.GET.get("accion", "")
    fecha_desde = request.GET.get("fecha_desde", "")
    fecha_hasta = request.GET.get("fecha_hasta", "")

    if usuario:
        registros = registros.filter(usuario_id=usuario)

    if modulo:
        registros = registros.filter(modulo=modulo)

    if accion:
        registros = registros.filter(accion=accion)

    if fecha_desde:
        registros = registros.filter(fecha__date__gte=fecha_desde)

    if fecha_hasta:
        registros = registros.filter(fecha__date__lte=fecha_hasta)

    # PAGINACIÓN

    paginator = Paginator(registros, 15)
    pagina = request.GET.get("page")
    registros_paginados = paginator.get_page(pagina)

    return render(
        request,
        "auditoria/aud_lista.html",
        {
            "registros": registros_paginados,
            "usuarios": __import__(
                "django.contrib.auth"
            ).contrib.auth.get_user_model().objects.all(),
            "modulos": RegistroAuditoria.Modulo.choices,
            "acciones": RegistroAuditoria.Accion.choices,
            "filtros": {
                "usuario": usuario,
                "modulo": modulo,
                "accion": accion,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
            }
        }
    )


@login_required
def auditoria_detalle(request, pk):
    verificar_acceso_auditoria(request.user)

    registro = get_object_or_404(
        RegistroAuditoria.objects.select_related("usuario"),
        pk=pk
    )

    return render(
        request,
        "auditoria/aud_detalle.html",
        {
            "registro": registro
        }
    )
