from rest_framework import serializers

from .models import TipoOrden, OrdenTrabajo


class TipoOrdenSerializer(serializers.ModelSerializer):

    class Meta:
        model = TipoOrden
        fields = [
            "id",
            "nombre",
            "descripcion",
            "activo",
        ]


class OrdenTrabajoSerializer(serializers.ModelSerializer):

    tipo_nombre = serializers.CharField(
        source="tipo.nombre",
        read_only=True,
    )

    plantilla_nombre = serializers.CharField(
        source="plantilla.nombre",
        read_only=True,
    )

    creado_por_nombre = serializers.CharField(
        source="creado_por.username",
        read_only=True,
    )

    estado_display = serializers.CharField(
        source="get_estado_display",
        read_only=True,
    )

    prioridad_display = serializers.CharField(
        source="get_prioridad_display",
        read_only=True,
    )

    class Meta:
        model = OrdenTrabajo

        fields = [
            "id",
            "numero",
            "nombre",
            "cliente",
            "descripcion",
            "tipo",
            "tipo_nombre",
            "plantilla",
            "plantilla_nombre",
            "estado",
            "estado_display",
            "prioridad",
            "prioridad_display",
            "fecha_creacion",
            "fecha_entrega",
            "creado_por",
            "creado_por_nombre",
        ]

        read_only_fields = [
            "id",
            "estado",
            "fecha_creacion",
            "creado_por",
        ]
