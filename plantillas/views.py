from django.db import transaction

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from .models import (
    PlantillaProceso,
    PlantillaEtapa,
    PlantillaActividad
)

from .serializers import (
    PlantillaProcesoSerializer,
    PlantillaEtapaSerializer,
    PlantillaActividadSerializer
)

from auditoria.services import registrar_evento


class PuedeGestionarPlantillas(BasePermission):
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


class PlantillaProcesoViewSet(viewsets.ModelViewSet):
    serializer_class = PlantillaProcesoSerializer
    permission_classes = [
        IsAuthenticated,
        PuedeGestionarPlantillas
    ]

    queryset = PlantillaProceso.objects.select_related(
        "tipo_orden"
    ).prefetch_related(
        "etapas__actividades"
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        tipo_orden = self.request.query_params.get("tipo_orden")
        activa = self.request.query_params.get("activa")

        if tipo_orden:
            queryset = queryset.filter(tipo_orden_id=tipo_orden)

        if activa is not None:
            queryset = queryset.filter(
                activa=activa.lower() == "true"
            )

        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user
        plantilla = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="plantillas",
            accion="creacion",
            descripcion=(
                f"Creó la plantilla de proceso '{plantilla.nombre}'."
            ),
            objeto_id=plantilla.id,
            objeto_referencia=plantilla.nombre
        )

    @transaction.atomic
    def perform_update(self, serializer):
        usuario = self.request.user
        plantilla = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="plantillas",
            accion="modificacion",
            descripcion=(
                f"Modificó la plantilla de proceso '{plantilla.nombre}'."
            ),
            objeto_id=plantilla.id,
            objeto_referencia=plantilla.nombre
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        usuario = self.request.user

        instance.activa = False
        instance.save(update_fields=["activa"])

        registrar_evento(
            usuario=usuario,
            modulo="plantillas",
            accion="desactivacion",
            descripcion=(
                f"Desactivó la plantilla de proceso '{instance.nombre}'."
            ),
            objeto_id=instance.id,
            objeto_referencia=instance.nombre
        )

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        plantilla = self.get_object()

        plantilla.activa = True
        plantilla.save(update_fields=["activa"])

        registrar_evento(
            usuario=request.user,
            modulo="plantillas",
            accion="reactivacion",
            descripcion=(
                f"Reactivó la plantilla de proceso '{plantilla.nombre}'."
            ),
            objeto_id=plantilla.id,
            objeto_referencia=plantilla.nombre
        )

        serializer = self.get_serializer(plantilla)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class PlantillaEtapaViewSet(viewsets.ModelViewSet):
    serializer_class = PlantillaEtapaSerializer
    permission_classes = [
        IsAuthenticated,
        PuedeGestionarPlantillas
    ]

    queryset = PlantillaEtapa.objects.select_related(
        "plantilla",
        "area"
    ).prefetch_related(
        "actividades"
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        plantilla = self.request.query_params.get("plantilla")

        if plantilla:
            queryset = queryset.filter(plantilla_id=plantilla)

        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user
        etapa = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="plantillas",
            accion="creacion",
            descripcion=(
                f"Creó la etapa '{etapa.nombre}' "
                f"en la plantilla '{etapa.plantilla.nombre}'."
            ),
            objeto_id=etapa.id,
            objeto_referencia=etapa.plantilla.nombre
        )

    @transaction.atomic
    def perform_update(self, serializer):
        usuario = self.request.user
        etapa = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="plantillas",
            accion="modificacion",
            descripcion=(
                f"Modificó la etapa '{etapa.nombre}' "
                f"de la plantilla '{etapa.plantilla.nombre}'."
            ),
            objeto_id=etapa.id,
            objeto_referencia=etapa.plantilla.nombre
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        usuario = self.request.user

        registrar_evento(
            usuario=usuario,
            modulo="plantillas",
            accion="eliminacion",
            descripcion=(
                f"Eliminó la etapa '{instance.nombre}' "
                f"de la plantilla '{instance.plantilla.nombre}'."
            ),
            objeto_id=instance.id,
            objeto_referencia=instance.plantilla.nombre
        )

        instance.delete()


class PlantillaActividadViewSet(viewsets.ModelViewSet):
    serializer_class = PlantillaActividadSerializer
    permission_classes = [
        IsAuthenticated,
        PuedeGestionarPlantillas
    ]

    queryset = PlantillaActividad.objects.select_related(
        "etapa",
        "etapa__plantilla"
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        etapa = self.request.query_params.get("etapa")

        if etapa:
            queryset = queryset.filter(etapa_id=etapa)

        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user
        actividad = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="plantillas",
            accion="creacion",
            descripcion=(
                f"Creó la actividad '{actividad.nombre}' "
                f"en la etapa '{actividad.etapa.nombre}' "
                f"de la plantilla '{actividad.etapa.plantilla.nombre}'."
            ),
            objeto_id=actividad.id,
            objeto_referencia=actividad.etapa.plantilla.nombre
        )

    @transaction.atomic
    def perform_update(self, serializer):
        usuario = self.request.user
        actividad = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="plantillas",
            accion="modificacion",
            descripcion=(
                f"Modificó la actividad '{actividad.nombre}' "
                f"de la etapa '{actividad.etapa.nombre}'."
            ),
            objeto_id=actividad.id,
            objeto_referencia=actividad.etapa.plantilla.nombre
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        usuario = self.request.user

        registrar_evento(
            usuario=usuario,
            modulo="plantillas",
            accion="eliminacion",
            descripcion=(
                f"Eliminó la actividad '{instance.nombre}' "
                f"de la etapa '{instance.etapa.nombre}'."
            ),
            objeto_id=instance.id,
            objeto_referencia=instance.etapa.plantilla.nombre
        )

        instance.delete()
