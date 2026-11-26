from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from auditoria.services import registrar_evento

from .models import (
    AreaProduccion,
    EtapaProduccion,
    Actividad,
    HistorialEtapa,
    HistorialActividad,
)

from .serializers import (
    AreaProduccionSerializer,
    EtapaProduccionSerializer,
    ActividadSerializer,
    HistorialEtapaSerializer,
    HistorialActividadSerializer,
)

from ordenes.models import OrdenTrabajo


# ==========================================================
# PERMISOS Y FUNCIONES AUXILIARES
# ==========================================================

def es_administrador(usuario):
    return (
        usuario.is_superuser
        or usuario.groups.filter(name="Administrador").exists()
    )


def puede_gestionar(usuario):
    return es_administrador(usuario)


class SoloLecturaOAdministrador(BasePermission):
    """
    Todos los usuarios autenticados pueden consultar.
    Solo los administradores pueden modificar.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        return puede_gestionar(request.user)


def siguiente_etapa_habilitada(etapa):
    """
    Permite iniciar una etapa únicamente cuando
    todas las etapas anteriores están completadas.
    """

    anteriores = EtapaProduccion.objects.filter(
        orden_trabajo_id=etapa.orden_trabajo_id,
        secuencia__lt=etapa.secuencia,
    )

    return not anteriores.exclude(
        estado=EtapaProduccion.Estado.COMPLETADA
    ).exists()


# ==========================================================
# CAMBIO DE ESTADO DE ETAPA
# ==========================================================

def cambiar_estado_etapa(etapa, nuevo_estado, usuario, observacion=""):
    """
    Gestiona las transiciones permitidas de una etapa,
    actualiza fechas, registra historial y auditoría.

    Cuando todas las etapas de una orden están completadas,
    cambia automáticamente el estado de la orden.
    """

    estados = EtapaProduccion.Estado

    transiciones = {
        estados.PENDIENTE: {
            estados.EN_PROCESO,
            estados.BLOQUEADA,
        },
        estados.EN_PROCESO: {
            estados.COMPLETADA,
            estados.BLOQUEADA,
        },
        estados.BLOQUEADA: {
            estados.EN_PROCESO,
        },
        estados.COMPLETADA: set(),
    }

    if nuevo_estado not in dict(estados.choices):
        raise ValueError("El estado seleccionado no es válido.")

    if not isinstance(observacion, str):
        raise ValueError("La observación debe ser un texto.")

    if len(observacion) > 500:
        raise ValueError(
            "La observación no puede superar los 500 caracteres."
        )

    if nuevo_estado == etapa.estado:
        return False

    if nuevo_estado not in transiciones[etapa.estado]:
        raise ValueError(
            "La transición de estado solicitada no está permitida."
        )

    # Bloquear y comprobar la orden asociada.
    orden = OrdenTrabajo.objects.select_for_update().get(
        pk=etapa.orden_trabajo_id
    )

    if orden.estado != OrdenTrabajo.Estado.EN_PROCESO:
        raise ValueError(
            "No se pueden modificar etapas de una orden que no está en proceso."
        )

    # Validar que las etapas anteriores estén completadas.
    if (
    etapa.estado == estados.PENDIENTE
    and nuevo_estado in {
        estados.EN_PROCESO,
        estados.BLOQUEADA,
    }
    and not siguiente_etapa_habilitada(etapa)
    ):raise ValueError(
        "Primero debes completar las etapas anteriores."
    )

    estado_anterior = etapa.estado
    ahora = timezone.now()

    etapa.estado = nuevo_estado
    campos = ["estado"]

    if (
        nuevo_estado == estados.EN_PROCESO
        and etapa.fecha_inicio is None
    ):
        etapa.fecha_inicio = ahora
        campos.append("fecha_inicio")

    if nuevo_estado == estados.COMPLETADA:
        etapa.fecha_fin = ahora
        campos.append("fecha_fin")

    elif estado_anterior == estados.COMPLETADA:
        etapa.fecha_fin = None
        campos.append("fecha_fin")

    etapa.save(update_fields=campos)

    # Registrar historial de la etapa.
    HistorialEtapa.objects.create(
        etapa=etapa,
        usuario=usuario,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        observacion=observacion,
    )

    registrar_evento(
        usuario=usuario,
        modulo="produccion",
        accion="cambio_estado",
        descripcion=(
            f"La etapa '{etapa.nombre}' de la orden "
            f"{orden.numero} cambió de "
            f"'{estado_anterior}' a '{nuevo_estado}'."
        ),
        objeto_id=etapa.id,
        objeto_referencia=orden.numero,
    )

    # Comprobar si todas las etapas de la orden terminaron.
    if nuevo_estado == estados.COMPLETADA:

        quedan_etapas_pendientes = (
            EtapaProduccion.objects
            .filter(orden_trabajo=orden)
            .exclude(estado=estados.COMPLETADA)
            .exists()
        )

        if not quedan_etapas_pendientes:

            orden.estado = OrdenTrabajo.Estado.COMPLETADA
            orden.save(update_fields=["estado"])

            registrar_evento(
                usuario=usuario,
                modulo="ordenes",
                accion="cambio_estado",
                descripcion=(
                    f"La orden '{orden.numero}' fue completada "
                    "automáticamente porque todas sus etapas "
                    "de producción finalizaron."
                ),
                objeto_id=orden.id,
                objeto_referencia=orden.numero,
            )

    # Actualizar el objeto relacionado para las respuestas.
    etapa.orden_trabajo.estado = orden.estado

    return True


# ==========================================================
# ÁREAS DE PRODUCCIÓN
# ==========================================================

class AreaProduccionViewSet(viewsets.ModelViewSet):

    serializer_class = AreaProduccionSerializer
    permission_classes = [SoloLecturaOAdministrador]

    def get_queryset(self):
        return AreaProduccion.objects.all()

    def perform_create(self, serializer):
        with transaction.atomic():

            area = serializer.save()

            registrar_evento(
                usuario=self.request.user,
                modulo="produccion",
                accion="creacion",
                descripcion=(
                    f"Se creó el área de producción: {area.nombre}."
                ),
                objeto_id=area.id,
                objeto_referencia=area.nombre,
            )

    def perform_update(self, serializer):
        with transaction.atomic():

            area = serializer.save()

            registrar_evento(
                usuario=self.request.user,
                modulo="produccion",
                accion="modificacion",
                descripcion=(
                    f"Se modificó el área de producción: {area.nombre}."
                ),
                objeto_id=area.id,
                objeto_referencia=area.nombre,
            )

    def perform_destroy(self, instance):
        if not instance.activo:
            return

        instance.activo = False
        instance.save(update_fields=["activo"])

        registrar_evento(
            usuario=self.request.user,
            modulo="produccion",
            accion="desactivacion",
            descripcion=(
                f"Se desactivó el área de producción: {instance.nombre}."
            ),
            objeto_id=instance.id,
            objeto_referencia=instance.nombre,
        )


# ==========================================================
# ETAPAS DE PRODUCCIÓN
# ==========================================================

class EtapaProduccionViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = EtapaProduccionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            EtapaProduccion.objects
            .select_related("orden_trabajo", "area")
            .prefetch_related("actividades")
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cambiar-estado",
        permission_classes=[SoloLecturaOAdministrador],
    )
    def cambiar_estado(self, request, pk=None):

        etapa = self.get_object()

        try:
            with transaction.atomic():

                etapa = (
                    EtapaProduccion.objects
                    .select_for_update()
                    .select_related("orden_trabajo")
                    .get(pk=etapa.pk)
                )

                cambio = cambiar_estado_etapa(
                    etapa,
                    request.data.get("estado", ""),
                    request.user,
                    request.data.get("observacion", ""),
                )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "mensaje": (
                "Estado actualizado."
                if cambio
                else "La etapa ya tenía ese estado."
            ),
            "etapa": self.get_serializer(etapa).data,
            "orden_estado": etapa.orden_trabajo.estado,
        })


# ==========================================================
# ACTIVIDADES
# SOLO CONSULTA
# ==========================================================

class ActividadViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ActividadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Actividad.objects.select_related(
            "etapa",
            "etapa__orden_trabajo",
        )


# ==========================================================
# HISTORIAL DE ETAPAS
# SOLO CONSULTA
# ==========================================================

class HistorialEtapaViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = HistorialEtapaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HistorialEtapa.objects.select_related(
            "etapa",
            "usuario",
        )


# ==========================================================
# HISTORIAL DE ACTIVIDADES
# SOLO CONSULTA
# ==========================================================

class HistorialActividadViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = HistorialActividadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HistorialActividad.objects.select_related(
            "actividad",
            "usuario",
        )


# ==========================================================
# PANEL PRINCIPAL DE PRODUCCIÓN
# ==========================================================

@login_required
def produccion_inicio(request):
    etapas = EtapaProduccion.objects.all()
    actividades = Actividad.objects.all()

    total_etapas = etapas.count()

    etapas_pendientes = etapas.filter(
        estado=EtapaProduccion.Estado.PENDIENTE
    ).count()

    etapas_en_proceso = etapas.filter(
        estado=EtapaProduccion.Estado.EN_PROCESO
    ).count()

    etapas_completadas = etapas.filter(
        estado=EtapaProduccion.Estado.COMPLETADA
    ).count()

    etapas_bloqueadas = etapas.filter(
        estado=EtapaProduccion.Estado.BLOQUEADA
    ).count()

    # Calcular porcentaje de avance
    porcentaje_completado = (
        round((etapas_completadas / total_etapas) * 100)
        if total_etapas > 0
        else 0
    )

    # Estadísticas de actividades
    total_actividades = actividades.count()

    actividades_pendientes = actividades.filter(
        estado=Actividad.Estado.PENDIENTE
    ).count()

    actividades_en_proceso = actividades.filter(
        estado=Actividad.Estado.EN_PROCESO
    ).count()

    actividades_completadas = actividades.filter(
        estado=Actividad.Estado.COMPLETADA
    ).count()

    contexto = {
        "total_etapas": total_etapas,
        "etapas_pendientes": etapas_pendientes,
        "etapas_en_proceso": etapas_en_proceso,
        "etapas_completadas": etapas_completadas,
        "etapas_bloqueadas": etapas_bloqueadas,

        "porcentaje_completado": porcentaje_completado,

        "total_actividades": total_actividades,
        "actividades_pendientes": actividades_pendientes,
        "actividades_en_proceso": actividades_en_proceso,
        "actividades_completadas": actividades_completadas,

        "puede_gestionar": puede_gestionar(request.user),
    }

    return render(
        request,
        "produccion/inicio.html",
        contexto
    )



# ==========================================================
# LISTADO DE ETAPAS
# ==========================================================

@login_required
def etapas_lista(request):

    etapas = (
        EtapaProduccion.objects
        .select_related("orden_trabajo", "area")
        .prefetch_related("actividades")
    )

    busqueda = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")

    if busqueda:
        etapas = etapas.filter(
            Q(nombre__icontains=busqueda)
            | Q(orden_trabajo__numero__icontains=busqueda)
            | Q(area__nombre__icontains=busqueda)
        )

    if estado in dict(EtapaProduccion.Estado.choices):
        etapas = etapas.filter(estado=estado)

    etapas = etapas.order_by(
        "orden_trabajo__fecha_creacion",
        "secuencia",
    )

    total_etapas = etapas.count()

    pagina = Paginator(etapas, 10).get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "produccion/etapas.html",
        {
            "etapas": pagina,
            "busqueda": busqueda,
            "estado_seleccionado": estado,
            "estados": EtapaProduccion.Estado.choices,
            "total_etapas": total_etapas,
            "puede_gestionar": puede_gestionar(request.user),
        },
    )


# ==========================================================
# CAMBIAR ESTADO DE UNA ETAPA DESDE EL DETALLE DE LA ORDEN
# ==========================================================

@login_required
@require_POST
@transaction.atomic
def etapa_cambiar_estado(request, pk):

    if not puede_gestionar(request.user):
        raise PermissionDenied(
            "No tienes permisos para modificar el avance de producción."
        )

    etapa = get_object_or_404(
        EtapaProduccion.objects
        .select_for_update()
        .select_related("orden_trabajo"),
        pk=pk,
    )

    try:
        cambio = cambiar_estado_etapa(
            etapa,
            request.POST.get("estado", ""),
            request.user,
            request.POST.get("observacion", ""),
        )

    except ValueError as exc:
        messages.error(request, str(exc))

    else:
        if (
            cambio
            and etapa.orden_trabajo.estado == OrdenTrabajo.Estado.COMPLETADA
        ):
            messages.success(
                request,
                "Etapa completada. Todas las etapas finalizaron y "
                "la orden de trabajo fue completada automáticamente.",
            )

        elif cambio:
            messages.success(
                request,
                "Estado de la etapa actualizado correctamente.",
            )

        else:
            messages.info(
                request,
                "La etapa ya tenía ese estado.",
            )

    return redirect(
        "ordenes:detalle",
        pk=etapa.orden_trabajo_id,
    )
