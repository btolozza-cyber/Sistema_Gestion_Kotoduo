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
        read_only=True
    )

    creado_por_nombre = serializers.CharField(
        source="creado_por.username",
        read_only=True
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
            "estado",
            "prioridad",
            "fecha_creacion",
            "fecha_entrega",
            "creado_por",
            "creado_por_nombre",
        ]

        read_only_fields = [
            "id",
            "fecha_creacion",
            "creado_por",
        ]
