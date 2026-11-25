from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import F

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .serializers import UsuarioSerializer

from ordenes.models import OrdenTrabajo
from produccion.models import EtapaProduccion
from alertas.models import Insumo, AlertaInsumo
from auditoria.models import RegistroAuditoria
from auditoria.services import registrar_evento


def es_administrador(usuario):
    return (
        usuario.is_superuser
        or usuario.groups.filter(name="Administrador").exists()
    )


def puede_ver_auditoria(usuario):
    return (
        es_administrador(usuario)
        or usuario.groups.filter(
            name="Supervisor de producción"
        ).exists()
    )


class IniciarSesionView(LoginView):
    template_name = "usuarios/login.html"
    redirect_authenticated_user = False

    def get_success_url(self):
        return reverse_lazy("dashboard")


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user

        if not (
            usuario.is_superuser
            or usuario.groups.filter(
                name__in=[
                    "Administrador",
                    "Supervisor de producción"
                ]
            ).exists()
        ):
            raise PermissionDenied(
                "No tienes permisos para consultar usuarios."
            )

        return User.objects.all().order_by("id")

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user

        if not es_administrador(usuario):
            raise PermissionDenied(
                "Solo un administrador puede crear usuarios."
            )

        nuevo_usuario = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="usuarios",
            accion="creacion",
            descripcion=(
                f"Creó el usuario '{nuevo_usuario.username}'."
            ),
            objeto_id=nuevo_usuario.id,
            objeto_referencia=nuevo_usuario.username
        )

    @transaction.atomic
    def perform_update(self, serializer):
        usuario = self.request.user

        if not es_administrador(usuario):
            raise PermissionDenied(
                "Solo un administrador puede modificar usuarios."
            )

        usuario_modificado = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="usuarios",
            accion="modificacion",
            descripcion=(
                f"Modificó los datos del usuario "
                f"'{usuario_modificado.username}'."
            ),
            objeto_id=usuario_modificado.id,
            objeto_referencia=usuario_modificado.username
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        usuario = request.user

        if not es_administrador(usuario):
            raise PermissionDenied(
                "Solo un administrador puede desactivar usuarios."
            )

        usuario_objetivo = self.get_object()

        usuario_objetivo.is_active = False
        usuario_objetivo.save(update_fields=["is_active"])

        registrar_evento(
            usuario=usuario,
            modulo="usuarios",
            accion="desactivacion",
            descripcion=(
                f"Desactivó el usuario "
                f"'{usuario_objetivo.username}'."
            ),
            objeto_id=usuario_objetivo.id,
            objeto_referencia=usuario_objetivo.username
        )

        return Response({
            "mensaje": "Usuario desactivado correctamente."
        })


@login_required
def dashboard(request):

    # Órdenes
    total_ordenes = OrdenTrabajo.objects.count()

    ordenes_completadas = OrdenTrabajo.objects.filter(
        estado="completada"
    ).count()

    # Etapas de producción
    etapas_pendientes = EtapaProduccion.objects.filter(
        estado="pendiente"
    ).count()

    etapas_en_proceso = EtapaProduccion.objects.filter(
        estado="en_proceso"
    ).count()

    etapas_completadas = EtapaProduccion.objects.filter(
        estado="completada"
    ).count()

    etapas_bloqueadas = EtapaProduccion.objects.filter(
        estado="bloqueada"
    ).count()

    total_etapas = (
        etapas_pendientes
        + etapas_en_proceso
        + etapas_completadas
        + etapas_bloqueadas
    )

    # Porcentajes de producción
    if total_etapas > 0:
        porcentaje_pendientes = round(
            etapas_pendientes / total_etapas * 100
        )
        porcentaje_en_proceso = round(
            etapas_en_proceso / total_etapas * 100
        )
        porcentaje_completadas = round(
            etapas_completadas / total_etapas * 100
        )
        porcentaje_bloqueadas = round(
            etapas_bloqueadas / total_etapas * 100
        )
    else:
        porcentaje_pendientes = 0
        porcentaje_en_proceso = 0
        porcentaje_completadas = 0
        porcentaje_bloqueadas = 0

    # Inventario
    insumos_activos = Insumo.objects.filter(activo=True)

    total_insumos = insumos_activos.count()

    insumos_stock_bajo = insumos_activos.filter(
        stock_actual__lte=F("stock_minimo")
    ).count()

    insumos_disponibles = total_insumos - insumos_stock_bajo

    # Alertas pendientes de resolución
    alertas_pendientes = AlertaInsumo.objects.filter(
        estado__in=["pendiente", "en_gestion"]
    ).count()

    # Auditoría: solo administradores y supervisores
    puede_ver_actividad = puede_ver_auditoria(request.user)

    actividades_recientes = []

    if puede_ver_actividad:
        actividades_recientes = (
            RegistroAuditoria.objects
            .select_related("usuario")
            .order_by("-fecha")[:5]
        )

    contexto = {
        "total_ordenes": total_ordenes,
        "ordenes_completadas": ordenes_completadas,

        "etapas_pendientes": etapas_pendientes,
        "etapas_en_proceso": etapas_en_proceso,
        "etapas_completadas": etapas_completadas,
        "etapas_bloqueadas": etapas_bloqueadas,

        "porcentaje_pendientes": porcentaje_pendientes,
        "porcentaje_en_proceso": porcentaje_en_proceso,
        "porcentaje_completadas": porcentaje_completadas,
        "porcentaje_bloqueadas": porcentaje_bloqueadas,

        "total_insumos": total_insumos,
        "insumos_disponibles": insumos_disponibles,
        "insumos_stock_bajo": insumos_stock_bajo,
        "alertas_pendientes": alertas_pendientes,

        "puede_ver_actividad": puede_ver_actividad,
        "actividades_recientes": actividades_recientes,
    }

    return render(request, "dashboard.html", contexto)
