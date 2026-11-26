from django.db import transaction, connection
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import TipoOrden, OrdenTrabajo
from .serializers import TipoOrdenSerializer, OrdenTrabajoSerializer
from .forms import OrdenTrabajoForm

from produccion.models import EtapaProduccion, Actividad
from plantillas.models import PlantillaEtapa
from auditoria.services import registrar_evento


# ========================================
# PERMISOS
# ========================================

def es_administrador(usuario):
    return usuario.is_superuser or usuario.groups.filter(
        name="Administrador"
    ).exists()


def puede_gestionar(usuario):
    return es_administrador(usuario)


# ========================================
# TIPOS DE ORDEN - API
# ========================================

class TipoOrdenViewSet(viewsets.ModelViewSet):

    queryset = TipoOrden.objects.all()
    serializer_class = TipoOrdenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if puede_gestionar(self.request.user):
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
            objeto_referencia=tipo.nombre,
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
            objeto_referencia=tipo.nombre,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        usuario = self.request.user

        if not puede_gestionar(usuario):
            raise PermissionDenied(
                "Solo un administrador puede desactivar tipos de órdenes."
            )

        instance.activo = False
        instance.save(update_fields=["activo"])

        registrar_evento(
            usuario=usuario,
            modulo="ordenes",
            accion="desactivacion",
            descripcion=f"Desactivó el tipo de orden '{instance.nombre}'.",
            objeto_id=instance.id,
            objeto_referencia=instance.nombre,
        )


# ========================================
# ÓRDENES DE TRABAJO - API
# ========================================

class OrdenTrabajoViewSet(viewsets.ModelViewSet):

    queryset = OrdenTrabajo.objects.all()
    serializer_class = OrdenTrabajoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrdenTrabajo.objects.select_related(
            "tipo",
            "plantilla",
            "creado_por",
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
            objeto_referencia=orden.numero,
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
            objeto_referencia=orden.numero,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        usuario = self.request.user

        if not puede_gestionar(usuario):
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
            objeto_referencia=instance.numero,
        )


# ========================================
# LISTADO DE ÓRDENES
# ========================================

@login_required
def ordenes_lista(request):

    usuario = request.user

    ordenes = OrdenTrabajo.objects.select_related(
        "tipo",
        "plantilla",
        "creado_por",
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
        for opcion in OrdenTrabajo._meta.get_field("estado").choices
    ]

    if estado in estados_disponibles:
        ordenes = ordenes.filter(estado=estado)

    # Filtro por prioridad
    prioridad = request.GET.get("prioridad", "")

    prioridades_disponibles = [
        opcion[0]
        for opcion in OrdenTrabajo._meta.get_field("prioridad").choices
    ]

    if prioridad in prioridades_disponibles:
        ordenes = ordenes.filter(prioridad=prioridad)

    # Ordenamiento
    ordenes = ordenes.order_by("-fecha_creacion")

    total_ordenes = ordenes.count()

    # Paginación
    paginador = Paginator(ordenes, 10)
    pagina = paginador.get_page(request.GET.get("page"))

    contexto = {
        "ordenes": pagina,
        "busqueda": busqueda,
        "estado_seleccionado": estado,
        "prioridad_seleccionada": prioridad,
        "estados": OrdenTrabajo._meta.get_field("estado").choices,
        "prioridades": OrdenTrabajo._meta.get_field("prioridad").choices,
        "total_ordenes": total_ordenes,
        "puede_crear": puede_gestionar(usuario),
        "puede_cancelar": es_administrador(request.user),
    }

    return render(
        request,
        "ordenes/lista.html",
        contexto,
    )

# ========================================
# CANCELAR ORDEN DE TRABAJO
# ========================================

@login_required
@require_POST
def orden_cancelar(request, pk):

    if not es_administrador(request.user):
        raise DjangoPermissionDenied(
            "Solo un administrador puede cancelar órdenes."
        )

    with transaction.atomic():

        orden = get_object_or_404(
            OrdenTrabajo.objects.select_for_update(),
            pk=pk
        )

        if orden.estado != OrdenTrabajo.Estado.PENDIENTE:
            messages.error(
                request,
                "Solo se pueden cancelar órdenes pendientes."
            )
            return redirect("ordenes:lista")

        if orden.etapas.exists():
            messages.error(
                request,
                "No se puede cancelar una orden que ya tiene etapas de producción."
            )
            return redirect("ordenes:lista")

        orden.estado = OrdenTrabajo.Estado.CANCELADA
        orden.save(update_fields=["estado"])

        registrar_evento(
            usuario=request.user,
            modulo="ordenes",
            accion="cambio_estado",
            descripcion=(
                f"Canceló la orden '{orden.numero}'."
            ),
            objeto_id=orden.id,
            objeto_referencia=orden.numero
        )

    messages.success(
        request,
        f"La orden {orden.numero} fue cancelada correctamente."
    )

    return redirect("ordenes:lista")

# ========================================
# REGISTRAR NUEVA ORDEN
# ========================================

@login_required
def orden_crear(request):

    usuario = request.user

    if not puede_gestionar(usuario):
        raise DjangoPermissionDenied(
            "No tienes permisos para crear órdenes de trabajo."
        )

    if request.method == "POST":

        formulario = OrdenTrabajoForm(request.POST)

        if formulario.is_valid():

            with transaction.atomic():

                # Evitar números duplicados simultáneos.
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT pg_advisory_xact_lock(%s)",
                            [728194],
                        )

                consecutivo = 0

                numeros_existentes = (
                    OrdenTrabajo.objects
                    .filter(numero__startswith="OT-")
                    .values_list("numero", flat=True)
                )

                for numero in numeros_existentes:
                    try:
                        numero_actual = int(numero.split("-")[1])
                        consecutivo = max(consecutivo, numero_actual)
                    except (IndexError, ValueError):
                        continue

                nuevo_numero = f"OT-{consecutivo + 1:04d}"

                orden = formulario.save(commit=False)

                orden.numero = nuevo_numero
                orden.creado_por = usuario
                orden.estado = OrdenTrabajo.Estado.PENDIENTE

                orden.save()

                registrar_evento(
                    usuario=usuario,
                    modulo="ordenes",
                    accion="creacion",
                    descripcion=(
                        f"Creó la orden de trabajo '{orden.numero}'."
                    ),
                    objeto_id=orden.id,
                    objeto_referencia=orden.numero,
                )

            messages.success(
                request,
                "La orden de trabajo fue creada correctamente.",
            )

            return redirect("ordenes:lista")

    else:
        formulario = OrdenTrabajoForm()

    return render(
        request,
        "ordenes/crear.html",
        {
            "formulario": formulario,
        },
    )


# ========================================
# DETALLE DE ORDEN DE TRABAJO
# ========================================

@login_required
def orden_detalle(request, pk):

    orden = get_object_or_404(
        OrdenTrabajo.objects.select_related(
            "tipo",
            "plantilla",
            "creado_por",
        ),
        pk=pk,
    )

    puede_gestionar_usuario = puede_gestionar(request.user)

    etapas = list(
        EtapaProduccion.objects.filter(
            orden_trabajo=orden,
        )
        .select_related("area")
        .prefetch_related("actividades")
        .order_by("secuencia")
    )

    anterior_completada = True

    for etapa in etapas:

        etapa.habilitada = anterior_completada

        etapa.puede_iniciar = (
            puede_gestionar_usuario
            and orden.estado == OrdenTrabajo.Estado.EN_PROCESO
            and etapa.estado == EtapaProduccion.Estado.PENDIENTE
            and anterior_completada
        )

        etapa.puede_completar = (
            puede_gestionar_usuario
            and orden.estado == OrdenTrabajo.Estado.EN_PROCESO
            and etapa.estado == EtapaProduccion.Estado.EN_PROCESO
        )

        etapa.puede_bloquear = (
              puede_gestionar_usuario
              and orden.estado == OrdenTrabajo.Estado.EN_PROCESO
              and anterior_completada
              and etapa.estado in [
                  EtapaProduccion.Estado.PENDIENTE,
                  EtapaProduccion.Estado.EN_PROCESO,
                  ]
        )

        etapa.puede_reanudar = (
            puede_gestionar_usuario
            and orden.estado == OrdenTrabajo.Estado.EN_PROCESO
            and etapa.estado == EtapaProduccion.Estado.BLOQUEADA
            and anterior_completada
        )

        if etapa.estado != EtapaProduccion.Estado.COMPLETADA:
            anterior_completada = False

    return render(
        request,
        "ordenes/detalle.html",
        {
            "orden": orden,
            "etapas": etapas,
            "puede_gestionar": puede_gestionar_usuario,
        },
    )


# ========================================
# INICIAR PRODUCCIÓN DESDE UNA PLANTILLA
# ========================================

@login_required
@require_POST
def orden_iniciar_produccion(request, pk):

    usuario = request.user

    if not puede_gestionar(usuario):
        raise DjangoPermissionDenied(
            "No tienes permisos para iniciar la producción."
        )

    with transaction.atomic():

        # Bloquear la orden durante el proceso.
        orden = get_object_or_404(
            OrdenTrabajo.objects.select_for_update(),
            pk=pk,
        )

        if orden.estado != OrdenTrabajo.Estado.PENDIENTE:
            messages.error(
                request,
                "La orden no se encuentra pendiente.",
            )
            return redirect("ordenes:detalle", pk=orden.pk)

        if orden.etapas.exists():
            messages.error(
                request,
                "La orden ya tiene etapas de producción registradas.",
            )
            return redirect("ordenes:detalle", pk=orden.pk)

        if not orden.plantilla:
            messages.error(
                request,
                "La orden no tiene una plantilla de producción asignada.",
            )
            return redirect("ordenes:detalle", pk=orden.pk)

        plantilla = orden.plantilla

        if not plantilla.activa:
            messages.error(
                request,
                "La plantilla seleccionada está inactiva.",
            )
            return redirect("ordenes:detalle", pk=orden.pk)

        if plantilla.tipo_orden_id != orden.tipo_id:
            messages.error(
                request,
                "La plantilla no corresponde al tipo de orden.",
            )
            return redirect("ordenes:detalle", pk=orden.pk)

        # Obtener etapas y actividades de la plantilla.
        etapas_plantilla = list(
            PlantillaEtapa.objects.filter(
                plantilla=plantilla,
            )
            .select_related("area")
            .prefetch_related("actividades")
            .order_by("secuencia")
        )

        if not etapas_plantilla:
            messages.error(
                request,
                "La plantilla no contiene etapas configuradas.",
            )
            return redirect("ordenes:detalle", pk=orden.pk)

        # Generar etapas y actividades para la orden.
        for etapa_base in etapas_plantilla:

            etapa = EtapaProduccion.objects.create(
                orden_trabajo=orden,
                area=etapa_base.area,
                nombre=etapa_base.nombre,
                descripcion=etapa_base.descripcion,
                secuencia=etapa_base.secuencia,
                estado=EtapaProduccion.Estado.PENDIENTE,
            )

            actividades_plantilla = (
                etapa_base.actividades.all().order_by("secuencia")
            )

            actividades_nuevas = [
                Actividad(
                    etapa=etapa,
                    nombre=actividad.nombre,
                    descripcion=actividad.descripcion,
                    secuencia=actividad.secuencia,
                    estado=Actividad.Estado.PENDIENTE,
                )
                for actividad in actividades_plantilla
            ]

            Actividad.objects.bulk_create(actividades_nuevas)

        # Cambiar estado de la orden.
        orden.estado = OrdenTrabajo.Estado.EN_PROCESO
        orden.save(update_fields=["estado"])

        registrar_evento(
            usuario=usuario,
            modulo="ordenes",
            accion="inicio_produccion",
            descripcion=(
                f"Inició la producción de la orden '{orden.numero}' "
                f"utilizando la plantilla '{plantilla.nombre}'. "
                f"Se generaron {len(etapas_plantilla)} etapas."
            ),
            objeto_id=orden.id,
            objeto_referencia=orden.numero,
        )

    messages.success(
        request,
        "La producción se inició correctamente. "
        "Las etapas y actividades fueron generadas desde la plantilla.",
    )

    return redirect("ordenes:detalle", pk=orden.pk)
