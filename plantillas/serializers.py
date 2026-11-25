from rest_framework import serializers
from .models import (
    PlantillaProceso,
    PlantillaEtapa,
    PlantillaActividad
)


class PlantillaActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantillaActividad
        fields = [
            "id",
            "etapa",
            "nombre",
            "descripcion",
            "secuencia"
        ]
        read_only_fields = ["id"]


class PlantillaEtapaSerializer(serializers.ModelSerializer):
    actividades = PlantillaActividadSerializer(
        many=True,
        read_only=True
    )
    area_nombre = serializers.CharField(
        source="area.nombre",
        read_only=True
    )

    class Meta:
        model = PlantillaEtapa
        fields = [
            "id",
            "plantilla",
            "area",
            "area_nombre",
            "nombre",
            "descripcion",
            "secuencia",
            "actividades"
        ]
        read_only_fields = ["id"]


class PlantillaProcesoSerializer(serializers.ModelSerializer):
    etapas = PlantillaEtapaSerializer(
        many=True,
        read_only=True
    )
    tipo_orden_nombre = serializers.CharField(
        source="tipo_orden.nombre",
        read_only=True
    )

    class Meta:
        model = PlantillaProceso
        fields = [
            "id",
            "tipo_orden",
            "tipo_orden_nombre",
            "nombre",
            "descripcion",
            "version",
            "activa",
            "fecha_creacion",
            "etapas"
        ]
        read_only_fields = ["id", "fecha_creacion"]
