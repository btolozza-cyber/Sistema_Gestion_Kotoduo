from django.db import transaction
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Insumo, AlertaInsumo, MovimientoInsumo
from .serializers import (
    InsumoSerializer,
    AlertaInsumoSerializer,
    MovimientoInsumoSerializer,
)

from auditoria.services import registrar_evento


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


def referencia_alerta(alerta):
    if alerta.orden_trabajo:
        return alerta.orden_trabajo.numero

    return f"Alerta #{alerta.id}"


def verificar_stock_bajo(insumo, usuario):
    alertas_automaticas = AlertaInsumo.objects.filter(
        insumo=insumo,
        automatica=True
    )

    if insumo.stock_actual <= insumo.stock_minimo:
        alerta_activa = alertas_automaticas.filter(
            estado__in=[
                AlertaInsumo.Estado.PENDIENTE,
                AlertaInsumo.Estado.EN_GESTION,
            ]
        ).exists()

        if not alerta_activa:
            alerta = AlertaInsumo.objects.create(
                insumo=insumo,
                registrado_por=usuario,
                automatica=True,
                cantidad_solicitada=max(
                    insumo.stock_minimo - insumo.stock_actual,
                    0
                ),
                descripcion=(
                    f"Alerta automática: el stock de '{insumo.nombre}' "
                    f"alcanzó el mínimo o está por debajo. "
                    f"Stock actual: {insumo.stock_actual} "
                    f"{insumo.unidad_medida}. "
                    f"Stock mínimo: {insumo.stock_minimo} "
                    f"{insumo.unidad_medida}."
                )
            )

            registrar_evento(
                usuario=usuario,
                modulo="alertas",
                accion="creacion",
                descripcion=(
                    f"El sistema generó una alerta automática de stock bajo "
                    f"para '{insumo.nombre}'."
                ),
                objeto_id=alerta.id,
                objeto_referencia=insumo.nombre
            )

    else:
        alertas_activas = alertas_automaticas.filter(
            estado__in=[
                AlertaInsumo.Estado.PENDIENTE,
                AlertaInsumo.Estado.EN_GESTION,
            ]
        )

        for alerta in alertas_activas:
            estado_anterior = alerta.estado

            alerta.estado = AlertaInsumo.Estado.RESUELTA
            alerta.fecha_resolucion = timezone.now()
            alerta.save(
                update_fields=["estado", "fecha_resolucion"]
            )

            registrar_evento(
                usuario=usuario,
                modulo="alertas",
                accion="cambio_estado",
                descripcion=(
                    f"El sistema resolvió automáticamente la alerta de "
                    f"stock bajo del insumo '{insumo.nombre}'. "
                    f"El stock actual es {insumo.stock_actual} "
                    f"{insumo.unidad_medida}, superando el mínimo de "
                    f"{insumo.stock_minimo}."
                ),
                objeto_id=alerta.id,
                objeto_referencia=insumo.nombre
            )


class InsumoViewSet(viewsets.ModelViewSet):
    serializer_class = InsumoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if puede_gestionar(self.request.user):
            return Insumo.objects.all()

        return Insumo.objects.filter(activo=True)

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "Solo administradores y supervisores pueden crear insumos."
            )

        insumo = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="alertas",
            accion="creacion",
            descripcion=f"Registró el insumo '{insumo.nombre}'.",
            objeto_id=insumo.id,
            objeto_referencia=insumo.nombre
        )

    @transaction.atomic
    def perform_update(self, serializer):
        usuario = self.request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "No tienes permiso para modificar insumos."
            )

        insumo = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="alertas",
            accion="modificacion",
            descripcion=f"Modificó el insumo '{insumo.nombre}'.",
            objeto_id=insumo.id,
            objeto_referencia=insumo.nombre
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        usuario = request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "No tienes permiso para desactivar insumos."
            )

        insumo = self.get_object()
        insumo.activo = False
        insumo.save(update_fields=["activo"])

        registrar_evento(
            usuario=usuario,
            modulo="alertas",
            accion="desactivacion",
            descripcion=f"Desactivó el insumo '{insumo.nombre}'.",
            objeto_id=insumo.id,
            objeto_referencia=insumo.nombre
        )

        return Response(
            {"mensaje": "Insumo desactivado correctamente."},
            status=status.HTTP_200_OK
        )


class MovimientoInsumoViewSet(viewsets.ModelViewSet):
    serializer_class = MovimientoInsumoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "Solo administradores y supervisores pueden consultar movimientos."
            )

        return MovimientoInsumo.objects.select_related(
            "insumo",
            "orden_trabajo",
            "registrado_por"
        ).all()

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "Solo administradores y supervisores pueden registrar movimientos."
            )

        datos = serializer.validated_data
        insumo_id = datos["insumo"].id
        tipo = datos["tipo"]
        cantidad = datos["cantidad"]

        try:
            insumo = Insumo.objects.select_for_update().get(
                id=insumo_id,
                activo=True
            )
        except Insumo.DoesNotExist:
            raise ValidationError({
                "insumo": "El insumo no existe o está inactivo."
            })

        stock_anterior = insumo.stock_actual

        if tipo == MovimientoInsumo.Tipo.SALIDA:
            if cantidad > stock_anterior:
                raise ValidationError({
                    "cantidad": (
                        f"Stock insuficiente. Disponible: {stock_anterior} "
                        f"{insumo.unidad_medida}."
                    )
                })

            insumo.stock_actual -= cantidad

        elif tipo == MovimientoInsumo.Tipo.ENTRADA:
            insumo.stock_actual += cantidad

        movimiento = serializer.save(
            insumo=insumo,
            registrado_por=usuario
        )

        insumo.save(update_fields=["stock_actual"])
        verificar_stock_bajo(insumo, usuario)

        accion_texto = (
            "entrada" if tipo == MovimientoInsumo.Tipo.ENTRADA
            else "salida"
        )

        referencia = (
            movimiento.orden_trabajo.numero
            if movimiento.orden_trabajo
            else insumo.nombre
        )

        registrar_evento(
            usuario=usuario,
            modulo="alertas",
            accion="creacion",
            descripcion=(
                f"Registró una {accion_texto} de {cantidad} "
                f"{insumo.unidad_medida} del insumo '{insumo.nombre}'. "
                f"Stock anterior: {stock_anterior}. "
                f"Stock actual: {insumo.stock_actual}."
            ),
            objeto_id=movimiento.id,
            objeto_referencia=referencia
        )

    def update(self, request, *args, **kwargs):
        raise PermissionDenied(
            "Los movimientos no se modifican. Registra un nuevo movimiento para corregir el stock."
        )

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied(
            "Los movimientos no se modifican. Registra un nuevo movimiento para corregir el stock."
        )

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied(
            "Los movimientos no se eliminan para preservar su trazabilidad."
        )


class AlertaInsumoViewSet(viewsets.ModelViewSet):
    serializer_class = AlertaInsumoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = AlertaInsumo.objects.select_related(
            "insumo",
            "orden_trabajo",
            "registrado_por"
        )

        if puede_gestionar(user):
            return queryset

        return queryset.filter(registrado_por=user)

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user

        if not (
            puede_gestionar(usuario)
            or es_operario(usuario)
        ):
            raise PermissionDenied(
                "No tienes permiso para registrar alertas."
            )

        insumo = serializer.validated_data["insumo"]

        if not insumo.activo:
            raise ValidationError({
                "insumo": "No se pueden registrar alertas con insumos inactivos."
            })

        alerta = serializer.save(registrado_por=usuario)

        registrar_evento(
            usuario=usuario,
            modulo="alertas",
            accion="creacion",
            descripcion=(
                f"Registró una alerta del insumo '{alerta.insumo.nombre}'. "
                f"Cantidad solicitada: {alerta.cantidad_solicitada}."
            ),
            objeto_id=alerta.id,
            objeto_referencia=referencia_alerta(alerta)
        )

    @transaction.atomic
    def perform_update(self, serializer):
        alerta = self.get_object()
        usuario = self.request.user

        estado_anterior = alerta.estado

        if puede_gestionar(usuario):
            alerta = serializer.save()

            if alerta.estado == AlertaInsumo.Estado.RESUELTA:
                if not alerta.fecha_resolucion:
                    alerta.fecha_resolucion = timezone.now()
                    alerta.save(update_fields=["fecha_resolucion"])

            elif alerta.fecha_resolucion:
                alerta.fecha_resolucion = None
                alerta.save(update_fields=["fecha_resolucion"])

        else:
            if (
                not es_operario(usuario)
                or alerta.registrado_por_id != usuario.id
            ):
                raise PermissionDenied(
                    "No tienes permiso para modificar esta alerta."
                )

            if alerta.estado != AlertaInsumo.Estado.PENDIENTE:
                raise PermissionDenied(
                    "Solo puedes modificar tus alertas pendientes."
                )

            campos_permitidos = {
                "cantidad_solicitada",
                "descripcion",
            }

            campos_recibidos = set(self.request.data.keys())

            if not campos_recibidos.issubset(campos_permitidos):
                raise PermissionDenied(
                    "Solo puedes modificar la cantidad y descripción de tu alerta."
                )

            alerta = serializer.save()

        if estado_anterior != alerta.estado:
            accion = "cambio_estado"
            descripcion = (
                f"Cambió el estado de la alerta #{alerta.id} "
                f"del insumo '{alerta.insumo.nombre}' "
                f"de '{estado_anterior}' a '{alerta.estado}'."
            )
        else:
            accion = "modificacion"
            descripcion = (
                f"Modificó la alerta #{alerta.id} "
                f"del insumo '{alerta.insumo.nombre}'."
            )

        registrar_evento(
            usuario=usuario,
            modulo="alertas",
            accion=accion,
            descripcion=descripcion,
            objeto_id=alerta.id,
            objeto_referencia=referencia_alerta(alerta)
        )

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied(
            "Las alertas no se eliminan para preservar su trazabilidad."
        )

