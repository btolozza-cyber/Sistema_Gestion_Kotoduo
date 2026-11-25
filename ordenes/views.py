from django.db import transaction
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

from produccion.models import EtapaProduccion

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import TipoOrden, OrdenTrabajo
from .serializers import TipoOrdenSerializer, OrdenTrabajoSerializer

from auditoria.services import registrar_evento


def es_administrador(usuario):
    return usuario.is_superuser or usuario.groups.filter(
        name="Administrador"
    ).exists()


def puede_gestionar(usuario):
    return usuario.is_superuser or usuario.groups.filter(
        name__in=["Administrador", "Supervisor de producción"]
    ).exists()


class TipoOrdenViewSet(viewsets.ModelViewSet):
    queryset = TipoOrden.objects.all()
    serializer_class = TipoOrdenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user

        if puede_gestionar(usuario):
            return TipoOrden.objects.all()

        return TipoOrden.objects.filter(activo=True)

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "No tienes permisos para crear tipos de órdenes."
            )

        tipo = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="ordenes",
            accion="creacion",
            descripcion=f"Creó el tipo de orden '{tipo.nombre}'.",
            objeto_id=tipo.id,
            objeto_referencia=tipo.nombre
        )

    @transaction.atomic
    def perform_update(self, serializer):
        usuario = self.request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "No tienes permisos para modificar tipos de órdenes."
            )

        tipo = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="ordenes",
            accion="modificacion",
            descripcion=f"Modificó el tipo de orden '{tipo.nombre}'.",
            objeto_id=tipo.id,
            objeto_referencia=tipo.nombre
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        usuario = self.request.user

        if not es_administrador(usuario):
            raise PermissionDenied(
                "Solo un administrador puede eliminar tipos de órdenes."
            )

        instance.activo = False
        instance.save(update_fields=["activo"])

        registrar_evento(
            usuario=usuario,
            modulo="ordenes",
            accion="desactivacion",
            descripcion=f"Desactivó el tipo de orden '{instance.nombre}'.",
            objeto_id=instance.id,
            objeto_referencia=instance.nombre
        )


class OrdenTrabajoViewSet(viewsets.ModelViewSet):
    queryset = OrdenTrabajo.objects.all()
    serializer_class = OrdenTrabajoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrdenTrabajo.objects.select_related(
            "tipo", "creado_por"
        ).all()

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "No tienes permisos para crear órdenes de trabajo."
            )

        orden = serializer.save(creado_por=usuario)

        registrar_evento(
            usuario=usuario,
            modulo="ordenes",
            accion="creacion",
            descripcion=f"Creó la orden de trabajo '{orden.numero}'.",
            objeto_id=orden.id,
            objeto_referencia=orden.numero
        )

    @transaction.atomic
    def perform_update(self, serializer):
        usuario = self.request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "No tienes permisos para modificar órdenes de trabajo."
            )

        instancia = self.get_object()
        estado_anterior = instancia.estado

        orden = serializer.save()

        if estado_anterior != orden.estado:
            accion = "cambio_estado"
            descripcion = (
                f"Cambió el estado de la orden '{orden.numero}' "
                f"de '{estado_anterior}' a '{orden.estado}'."
            )
        else:
            accion = "modificacion"
            descripcion = (
                f"Modificó la orden de trabajo '{orden.numero}'."
            )

        registrar_evento(
            usuario=usuario,
            modulo="ordenes",
            accion=accion,
            descripcion=descripcion,
            objeto_id=orden.id,
            objeto_referencia=orden.numero
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        usuario = self.request.user

        if not es_administrador(usuario):
            raise PermissionDenied(
                "Solo un administrador puede cancelar órdenes."
            )

        estado_anterior = instance.estado

        instance.estado = OrdenTrabajo.Estado.CANCELADA
        instance.save(update_fields=["estado"])

        registrar_evento(
            usuario=usuario,
            modulo="ordenes",
            accion="cambio_estado",
            descripcion=(
                f"Canceló la orden '{instance.numero}'. "
                f"Estado anterior: '{estado_anterior}'. "
                f"Estado nuevo: '{instance.estado}'."
            ),
            objeto_id=instance.id,
            objeto_referencia=instance.numero
        )

@login_required
def ordenes_lista(request):

    usuario = request.user

    # Consulta inicial
    ordenes = OrdenTrabajo.objects.select_related(
        "tipo",
        "creado_por"
    )

    # Restricción de acceso según el rol
    if not puede_gestionar(usuario):
        ordenes_asignadas = EtapaProduccion.objects.filter(
            responsable=usuario
        ).values_list("orden_trabajo_id", flat=True)

        ordenes = ordenes.filter(
            id__in=ordenes_asignadas
        )

    # Buscador
    busqueda = request.GET.get("q", "").strip()

    if busqueda:
        ordenes = ordenes.filter(
            Q(numero__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
            | Q(cliente__icontains=busqueda)
        )

    # Filtro por estado
    estado = request.GET.get("estado", "")

    estados_disponibles = [
        opcion[0]
        for opcion in OrdenTrabajo._meta.get_field(
            "estado"
        ).choices
    ]

    if estado in estados_disponibles:
        ordenes = ordenes.filter(estado=estado)

    # Filtro por prioridad
    prioridad = request.GET.get("prioridad", "")

    prioridades_disponibles = [
        opcion[0]
        for opcion in OrdenTrabajo._meta.get_field(
            "prioridad"
        ).choices
    ]

    if prioridad in prioridades_disponibles:
        ordenes = ordenes.filter(prioridad=prioridad)

    # Ordenamiento
    ordenes = ordenes.order_by("-fecha_creacion")

    # Paginación
    paginador = Paginator(ordenes, 10)
    pagina = paginador.get_page(request.GET.get("page"))

    contexto = {
        "ordenes": pagina,
        "busqueda": busqueda,
        "estado_seleccionado": estado,
        "prioridad_seleccionada": prioridad,
        "estados": OrdenTrabajo._meta.get_field(
            "estado"
        ).choices,
        "prioridades": OrdenTrabajo._meta.get_field(
            "prioridad"
        ).choices,
        "total_ordenes": ordenes.count(),
    }

    return render(
        request,
        "ordenes/lista.html",
        contexto
    )

