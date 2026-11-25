from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
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


# ==========================================================
# FUNCIONES AUXILIARES Y ROLES
# ==========================================================

def es_admin(user):
    return (
        user.is_superuser
        or user.groups.filter(name="Administrador").exists()
    )


def es_supervisor(user):
    return user.groups.filter(
        name="Supervisor de producción"
    ).exists()


def es_operario(user):
    return user.groups.filter(name="Operario").exists()


def puede_gestionar(user):
    return es_admin(user) or es_supervisor(user)


def obtener_observacion(request):
    observacion = request.data.get("observacion", "")

    if not isinstance(observacion, str):
        raise ValidationError({
            "observacion": "La observación debe ser un texto."
        })

    if len(observacion) > 500:
        raise ValidationError({
            "observacion": "La observación no puede superar los 500 caracteres."
        })

    return observacion


def sincronizar_fechas(
    instancia,
    estado_nuevo,
    estado_en_proceso,
    estado_completada,
    estado_anterior=None
):
    """
    Actualiza las fechas según el estado actual.
    Devuelve los campos que necesitan guardarse.
    """

    ahora = timezone.now()
    campos = []

    if (
        estado_nuevo == estado_en_proceso
        and instancia.fecha_inicio is None
    ):
        instancia.fecha_inicio = ahora
        campos.append("fecha_inicio")

    if (
        estado_nuevo == estado_completada
        and instancia.fecha_fin is None
    ):
        instancia.fecha_fin = ahora
        campos.append("fecha_fin")

    elif (
        estado_anterior == estado_completada
        and estado_nuevo != estado_completada
    ):
        instancia.fecha_fin = None
        campos.append("fecha_fin")

    return campos


def hay_cambios(serializer):
    """
    Comprueba si los datos recibidos modifican algún campo.
    """

    instancia = serializer.instance

    return any(
        getattr(instancia, campo) != valor
        for campo, valor in serializer.validated_data.items()
    )


# ==========================================================
# ÁREAS DE PRODUCCIÓN
# ==========================================================

class AreaProduccionViewSet(viewsets.ModelViewSet):
    serializer_class = AreaProduccionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if puede_gestionar(self.request.user):
            return AreaProduccion.objects.all()

        return AreaProduccion.objects.filter(activo=True)

    def perform_create(self, serializer):
        if not puede_gestionar(self.request.user):
            raise PermissionDenied(
                "No tienes permiso para crear áreas de producción."
            )

        with transaction.atomic():
            area = serializer.save()

            registrar_evento(
                usuario=self.request.user,
                modulo="produccion",
                accion="creacion",
                descripcion=f"Se creó el área de producción: {area.nombre}.",
                objeto_id=area.id,
                objeto_referencia=area.nombre
            )

    def perform_update(self, serializer):
        if not puede_gestionar(self.request.user):
            raise PermissionDenied(
                "No tienes permiso para modificar áreas de producción."
            )

        area = serializer.instance

        if not hay_cambios(serializer):
            serializer.save()
            return

        with transaction.atomic():
            area = serializer.save()

            registrar_evento(
                usuario=self.request.user,
                modulo="produccion",
                accion="modificacion",
                descripcion=f"Se modificó el área de producción: {area.nombre}.",
                objeto_id=area.id,
                objeto_referencia=area.nombre
            )

    def destroy(self, request, *args, **kwargs):
        if not puede_gestionar(request.user):
            raise PermissionDenied(
                "No tienes permiso para desactivar áreas."
            )

        area = self.get_object()

        if not area.activo:
            return Response(
                {"mensaje": "El área ya se encuentra desactivada."},
                status=status.HTTP_200_OK
            )

        with transaction.atomic():
            area.activo = False
            area.save(update_fields=["activo"])

            registrar_evento(
                usuario=request.user,
                modulo="produccion",
                accion="desactivacion",
                descripcion=f"Se desactivó el área de producción: {area.nombre}.",
                objeto_id=area.id,
                objeto_referencia=area.nombre
            )

        return Response(
            {"mensaje": "Área desactivada correctamente."},
            status=status.HTTP_200_OK
        )


# ==========================================================
# ETAPAS DE PRODUCCIÓN
# ==========================================================

class EtapaProduccionViewSet(viewsets.ModelViewSet):
    serializer_class = EtapaProduccionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = EtapaProduccion.objects.select_related(
            "orden_trabajo",
            "area",
            "responsable"
        ).prefetch_related("actividades")

        if puede_gestionar(user):
            return queryset

        return queryset.filter(
            Q(responsable=user)
            | Q(actividades__responsable=user)
        ).distinct()

    def perform_create(self, serializer):
        if not puede_gestionar(self.request.user):
            raise PermissionDenied(
                "Solo administradores y supervisores pueden crear etapas."
            )

        with transaction.atomic():
            etapa = serializer.save()

            campos = sincronizar_fechas(
                etapa,
                etapa.estado,
                EtapaProduccion.Estado.EN_PROCESO,
                EtapaProduccion.Estado.COMPLETADA
            )

            if campos:
                etapa.save(update_fields=campos)

            registrar_evento(
                usuario=self.request.user,
                modulo="produccion",
                accion="creacion",
                descripcion=f"Se creó la etapa '{etapa.nombre}' para la orden {etapa.orden_trabajo.numero}.",
                objeto_id=etapa.id,
                objeto_referencia=etapa.orden_trabajo.numero
            )

    def perform_update(self, serializer):
        if not puede_gestionar(self.request.user):
            raise PermissionDenied(
                "No tienes permiso para modificar etapas."
            )

        etapa = serializer.instance
        estado_anterior = etapa.estado
        observacion = obtener_observacion(self.request)
        hubo_cambios = hay_cambios(serializer)

        with transaction.atomic():
            etapa = serializer.save()

            campos = sincronizar_fechas(
                etapa,
                etapa.estado,
                EtapaProduccion.Estado.EN_PROCESO,
                EtapaProduccion.Estado.COMPLETADA,
                estado_anterior
            )

            if campos:
                etapa.save(update_fields=campos)

            if estado_anterior != etapa.estado:
                HistorialEtapa.objects.create(
                    etapa=etapa,
                    usuario=self.request.user,
                    estado_anterior=estado_anterior,
                    estado_nuevo=etapa.estado,
                    observacion=observacion
                )

                registrar_evento(
                    usuario=self.request.user,
                    modulo="produccion",
                    accion="cambio_estado",
                    descripcion=(
                        f"La etapa '{etapa.nombre}' de la orden "
                        f"{etapa.orden_trabajo.numero} cambió de "
                        f"'{estado_anterior}' a '{etapa.estado}'."
                    ),
                    objeto_id=etapa.id,
                    objeto_referencia=etapa.orden_trabajo.numero
                )

            elif hubo_cambios:
                registrar_evento(
                    usuario=self.request.user,
                    modulo="produccion",
                    accion="modificacion",
                    descripcion=(
                        f"Se modificó la etapa '{etapa.nombre}' "
                        f"de la orden {etapa.orden_trabajo.numero}."
                    ),
                    objeto_id=etapa.id,
                    objeto_referencia=etapa.orden_trabajo.numero
                )

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied(
            "Las etapas no se pueden eliminar para preservar la trazabilidad."
        )


# ==========================================================
# ACTIVIDADES
# ==========================================================

class ActividadViewSet(viewsets.ModelViewSet):
    serializer_class = ActividadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Actividad.objects.select_related(
            "etapa",
            "responsable",
            "etapa__orden_trabajo"
        )

        if puede_gestionar(user):
            return queryset

        return queryset.filter(responsable=user)

    def perform_create(self, serializer):
        if not puede_gestionar(self.request.user):
            raise PermissionDenied(
                "Solo administradores y supervisores pueden crear actividades."
            )

        with transaction.atomic():
            actividad = serializer.save()

            campos = sincronizar_fechas(
                actividad,
                actividad.estado,
                Actividad.Estado.EN_PROCESO,
                Actividad.Estado.COMPLETADA
            )

            if campos:
                actividad.save(update_fields=campos)

            numero_orden = actividad.etapa.orden_trabajo.numero

            registrar_evento(
                usuario=self.request.user,
                modulo="produccion",
                accion="creacion",
                descripcion=(
                    f"Se creó la actividad '{actividad.nombre}' "
                    f"en la etapa '{actividad.etapa.nombre}' "
                    f"de la orden {numero_orden}."
                ),
                objeto_id=actividad.id,
                objeto_referencia=numero_orden
            )

    def perform_update(self, serializer):
        if not puede_gestionar(self.request.user):
            raise PermissionDenied(
                "No tienes permiso para modificar actividades directamente."
            )

        actividad = serializer.instance
        estado_anterior = actividad.estado
        observacion = obtener_observacion(self.request)
        hubo_cambios = hay_cambios(serializer)

        with transaction.atomic():
            actividad = serializer.save()

            campos = sincronizar_fechas(
                actividad,
                actividad.estado,
                Actividad.Estado.EN_PROCESO,
                Actividad.Estado.COMPLETADA,
                estado_anterior
            )

            if campos:
                actividad.save(update_fields=campos)

            numero_orden = actividad.etapa.orden_trabajo.numero

            if estado_anterior != actividad.estado:
                HistorialActividad.objects.create(
                    actividad=actividad,
                    usuario=self.request.user,
                    estado_anterior=estado_anterior,
                    estado_nuevo=actividad.estado,
                    observacion=observacion
                )

                registrar_evento(
                    usuario=self.request.user,
                    modulo="produccion",
                    accion="cambio_estado",
                    descripcion=(
                        f"La actividad '{actividad.nombre}' de la orden "
                        f"{numero_orden} cambió de "
                        f"'{estado_anterior}' a '{actividad.estado}'."
                    ),
                    objeto_id=actividad.id,
                    objeto_referencia=numero_orden
                )

            elif hubo_cambios:
                registrar_evento(
                    usuario=self.request.user,
                    modulo="produccion",
                    accion="modificacion",
                    descripcion=(
                        f"Se modificó la actividad '{actividad.nombre}' "
                        f"de la orden {numero_orden}."
                    ),
                    objeto_id=actividad.id,
                    objeto_referencia=numero_orden
                )

    @action(
        detail=True,
        methods=["patch"],
        url_path="actualizar-estado"
    )
    def actualizar_estado(self, request, pk=None):
        actividad = self.get_object()
        user = request.user

        if not puede_gestionar(user):
            if (
                not es_operario(user)
                or actividad.responsable_id != user.id
            ):
                raise PermissionDenied(
                    "Solo puedes actualizar tus propias actividades asignadas."
                )

        nuevo_estado = request.data.get("estado")

        estados_validos = [
            choice[0] for choice in Actividad.Estado.choices
        ]

        if nuevo_estado not in estados_validos:
            return Response(
                {"error": "El estado indicado no es válido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        observacion = obtener_observacion(request)
        estado_anterior = actividad.estado

        with transaction.atomic():
            actividad.estado = nuevo_estado

            campos = []

            if estado_anterior != nuevo_estado:
                campos.append("estado")

            campos_fecha = sincronizar_fechas(
                actividad,
                nuevo_estado,
                Actividad.Estado.EN_PROCESO,
                Actividad.Estado.COMPLETADA,
                estado_anterior
            )

            campos.extend(campos_fecha)

            if campos:
                actividad.save(update_fields=list(set(campos)))

            if estado_anterior != nuevo_estado:
                HistorialActividad.objects.create(
                    actividad=actividad,
                    usuario=user,
                    estado_anterior=estado_anterior,
                    estado_nuevo=nuevo_estado,
                    observacion=observacion
                )

                numero_orden = actividad.etapa.orden_trabajo.numero

                registrar_evento(
                    usuario=user,
                    modulo="produccion",
                    accion="cambio_estado",
                    descripcion=(
                        f"El operario {user.username} cambió la actividad "
                        f"'{actividad.nombre}' de la orden {numero_orden} "
                        f"de '{estado_anterior}' a '{nuevo_estado}'."
                    ),
                    objeto_id=actividad.id,
                    objeto_referencia=numero_orden
                )

        return Response(self.get_serializer(actividad).data)

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied(
            "Las actividades no se pueden eliminar para preservar la trazabilidad."
        )


# ==========================================================
# HISTORIAL DE ETAPAS (SOLO LECTURA)
# ==========================================================

class HistorialEtapaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HistorialEtapaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = HistorialEtapa.objects.select_related(
            "etapa",
            "usuario"
        )

        if puede_gestionar(user):
            return queryset

        return queryset.filter(
            Q(etapa__responsable=user)
            | Q(etapa__actividades__responsable=user)
        ).distinct()


# ==========================================================
# HISTORIAL DE ACTIVIDADES (SOLO LECTURA)
# ==========================================================

class HistorialActividadViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HistorialActividadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = HistorialActividad.objects.select_related(
            "actividad",
            "usuario"
        )

        if puede_gestionar(user):
            return queryset

        return queryset.filter(
            actividad__responsable=user
        )
