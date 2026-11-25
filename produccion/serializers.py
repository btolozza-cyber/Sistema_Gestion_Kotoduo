from rest_framework import serializers

from .models import (
    AreaProduccion,
    EtapaProduccion,
    Actividad,
    HistorialEtapa,
    HistorialActividad,
)


class AreaProduccionSerializer(serializers.ModelSerializer):

    class Meta:
        model = AreaProduccion
        fields = [
            "id",
            "nombre",
            "descripcion",
            "activo",
        ]


class EtapaProduccionSerializer(serializers.ModelSerializer):

    orden_numero = serializers.CharField(
        source="orden_trabajo.numero",
        read_only=True
    )

    area_nombre = serializers.CharField(
        source="area.nombre",
        read_only=True
    )

    responsable_nombre = serializers.CharField(
        source="responsable.username",
        read_only=True
    )

    class Meta:
        model = EtapaProduccion
        fields = [
            "id",
            "orden_trabajo",
            "orden_numero",
            "area",
            "area_nombre",
            "responsable",
            "responsable_nombre",
            "nombre",
            "descripcion",
            "secuencia",
            "estado",
            "fecha_inicio",
            "fecha_fin",
        ]

        read_only_fields = [
            "id",
            "fecha_inicio",
            "fecha_fin",
        ]


class ActividadSerializer(serializers.ModelSerializer):

    etapa_nombre = serializers.CharField(
        source="etapa.nombre",
        read_only=True
    )

    responsable_nombre = serializers.CharField(
        source="responsable.username",
        read_only=True
    )

    class Meta:
        model = Actividad
        fields = [
            "id",
            "etapa",
            "etapa_nombre",
            "responsable",
            "responsable_nombre",
            "nombre",
            "descripcion",
            "estado",
            "fecha_inicio",
            "fecha_fin",
        ]

        read_only_fields = [
            "id",
            "fecha_inicio",
            "fecha_fin",
        ]


class HistorialEtapaSerializer(serializers.ModelSerializer):

    usuario_nombre = serializers.CharField(
        source="usuario.username",
        read_only=True
    )

    class Meta:
        model = HistorialEtapa
        fields = [
            "id",
            "etapa",
            "usuario",
            "usuario_nombre",
            "estado_anterior",
            "estado_nuevo",
            "observacion",
            "fecha",
        ]

        read_only_fields = fields


class HistorialActividadSerializer(serializers.ModelSerializer):

    usuario_nombre = serializers.CharField(
        source="usuario.username",
        read_only=True
    )

    class Meta:
        model = HistorialActividad
        fields = [
            "id",
            "actividad",
            "usuario",
            "usuario_nombre",
            "estado_anterior",
            "estado_nuevo",
            "observacion",
            "fecha",
        ]

        read_only_fields = fields
