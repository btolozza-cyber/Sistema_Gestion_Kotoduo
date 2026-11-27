from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction, models
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
    SAFE_METHODS,
)
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

def es_administrador(usuario):
    return (
        usuario.is_authenticated
        and (
            usuario.is_superuser
            or usuario.groups.filter(name="Administrador").exists()
        )
    )


def puede_gestionar(usuario):
    """
    Permite administrar áreas de producción.
    Exclusivo del Administrador.
    """
    return es_administrador(usuario)


def puede_gestionar_etapas(usuario):
    """
    Permite gestionar el avance de producción.
    Administrador y Supervisor de producción.
    """
    return (
        es_administrador(usuario)
        or usuario.groups.filter(
            name="Supervisor de producción"
        ).exists()
    )


class SoloLecturaOAdministrador(BasePermission):
    """
    Todos los usuarios autenticados pueden consultar.
    Solo los administradores pueden modificar.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return puede_gestionar(request.user)


class SoloLecturaAdministradorOSupervisor(BasePermission):
    """
    Todos los usuarios autenticados pueden consultar.
    Administradores y supervisores pueden modificar.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return puede_gestionar_etapas(request.user)


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

    orden = OrdenTrabajo.objects.select_for_update().get(
        pk=etapa.orden_trabajo_id
    )

    if orden.estado != OrdenTrabajo.Estado.EN_PROCESO:
        raise ValueError(
            "No se pueden modificar etapas de una orden que no está en proceso."
        )

    if (
        etapa.estado == estados.PENDIENTE
        and nuevo_estado in {
            estados.EN_PROCESO,
            estados.BLOQUEADA,
        }
        and not siguiente_etapa_habilitada(etapa)
    ):
        raise ValueError(
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

    etapa.orden_trabajo.estado = orden.estado

    return True

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
        permission_classes=[SoloLecturaAdministradorOSupervisor],
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


class ActividadViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ActividadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Actividad.objects.select_related(
            "etapa",
            "etapa__orden_trabajo",
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cambiar-estado",
        permission_classes=[SoloLecturaAdministradorOSupervisor],
    )
    def cambiar_estado(self, request, pk=None):

        actividad = self.get_object()

        nuevo_estado = request.data.get("estado", "")
        observacion = request.data.get("observacion", "")

        if nuevo_estado not in dict(Actividad.Estado.choices):
            return Response(
                {"error": "El estado seleccionado no es válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(observacion, str):
            return Response(
                {"error": "La observación debe ser un texto."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(observacion) > 500:
            return Response(
                {
                    "error": (
                        "La observación no puede superar "
                        "los 500 caracteres."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():

                actividad = (
                    Actividad.objects
                    .select_for_update()
                    .get(pk=actividad.pk)
                )

                estado_anterior = actividad.estado

                if nuevo_estado == estado_anterior:
                    return Response({
                        "mensaje": "La actividad ya tenía ese estado."
                    })

                ahora = timezone.now()

                actividad.estado = nuevo_estado
                campos = ["estado"]

                if (
                    nuevo_estado == Actividad.Estado.EN_PROCESO
                    and actividad.fecha_inicio is None
                ):
                    actividad.fecha_inicio = ahora
                    campos.append("fecha_inicio")

                if nuevo_estado == Actividad.Estado.COMPLETADA:
                    actividad.fecha_fin = ahora
                    campos.append("fecha_fin")

                elif estado_anterior == Actividad.Estado.COMPLETADA:
                    actividad.fecha_fin = None
                    campos.append("fecha_fin")

                actividad.save(update_fields=campos)

                HistorialActividad.objects.create(
                    actividad=actividad,
                    usuario=request.user,
                    estado_anterior=estado_anterior,
                    estado_nuevo=nuevo_estado,
                    observacion=observacion,
                )

                registrar_evento(
                    usuario=request.user,
                    modulo="produccion",
                    accion="cambio_estado",
                    descripcion=(
                        f"La actividad '{actividad.nombre}' "
                        f"cambió de '{estado_anterior}' "
                        f"a '{nuevo_estado}'."
                    ),
                    objeto_id=actividad.id,
                    objeto_referencia=actividad.nombre,
                )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "mensaje": (
                "Estado de la actividad actualizado correctamente."
            ),
            "actividad": self.get_serializer(actividad).data,
        })


class HistorialEtapaViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = HistorialEtapaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HistorialEtapa.objects.select_related(
            "etapa",
            "usuario",
        )


class HistorialActividadViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = HistorialActividadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HistorialActividad.objects.select_related(
            "actividad",
            "usuario",
        )


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

    porcentaje_completado = (
        round((etapas_completadas / total_etapas) * 100)
        if total_etapas > 0
        else 0
    )

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
        "puede_cambiar_estado_etapas": puede_gestionar_etapas(
            request.user
        ),
    }

    return render(
        request,
        "produccion/inicio.html",
        contexto,
    )



@login_required
def etapas_lista(request):

    # Obtener órdenes que tengan etapas de producción
    ordenes = (
        OrdenTrabajo.objects
        .filter(etapas__isnull=False)
        .distinct()
        .prefetch_related(
            models.Prefetch(
                "etapas",
                queryset=(
                    EtapaProduccion.objects
                    .select_related("area")
                    .prefetch_related("actividades")
                    .order_by("secuencia")
                ),
                to_attr="etapas_ordenadas"
            )
        )
        .order_by("-fecha_creacion")
    )

    busqueda = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")

    resultados = []

    for orden in ordenes:

        etapas_ordenadas = orden.etapas_ordenadas

        if not etapas_ordenadas:
            continue

        # Buscar la primera etapa que todavía no esté completada
        etapa_actual = next(
            (
                etapa
                for etapa in etapas_ordenadas
                if etapa.estado != EtapaProduccion.Estado.COMPLETADA
            ),
            etapas_ordenadas[-1]
        )

        # Filtro por búsqueda
        if busqueda:
            coincide = (
                busqueda.lower() in orden.numero.lower()
                or busqueda.lower() in orden.nombre.lower()
                or busqueda.lower() in etapa_actual.nombre.lower()
                or busqueda.lower() in etapa_actual.area.nombre.lower()
            )

            if not coincide:
                continue

        # Filtro por estado de la etapa actual
        if estado and etapa_actual.estado != estado:
            continue

        # Guardar información de la orden y su etapa actual
        orden.etapa_actual = etapa_actual
        orden.total_etapas = len(etapas_ordenadas)

        resultados.append(orden)

    total_etapas = len(resultados)

    pagina = Paginator(resultados, 10).get_page(
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
            "puede_cambiar_estado_etapas": puede_gestionar_etapas(
                request.user
            ),
        },
    )


@login_required
@require_POST
@transaction.atomic
def etapa_cambiar_estado(request, pk):

    if not puede_gestionar_etapas(request.user):
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
