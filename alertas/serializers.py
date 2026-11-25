from rest_framework import serializers

from .models import Insumo, AlertaInsumo, MovimientoInsumo


class InsumoSerializer(serializers.ModelSerializer):

    stock_bajo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Insumo
        fields = [
            "id",
            "nombre",
            "descripcion",
            "unidad_medida",
            "stock_actual",
            "stock_minimo",
            "stock_bajo",
            "activo",
        ]

        read_only_fields = [
            "id",
            "stock_actual",
            "stock_bajo",
        ]


class MovimientoInsumoSerializer(serializers.ModelSerializer):

    insumo_nombre = serializers.CharField(
        source="insumo.nombre",
        read_only=True
    )

    orden_numero = serializers.CharField(
        source="orden_trabajo.numero",
        read_only=True,
        allow_null=True
    )

    registrado_por_nombre = serializers.CharField(
        source="registrado_por.username",
        read_only=True
    )

    tipo_display = serializers.CharField(
        source="get_tipo_display",
        read_only=True
    )

    class Meta:
        model = MovimientoInsumo
        fields = [
            "id",
            "insumo",
            "insumo_nombre",
            "tipo",
            "tipo_display",
            "cantidad",
            "orden_trabajo",
            "orden_numero",
            "registrado_por",
            "registrado_por_nombre",
            "descripcion",
            "fecha",
        ]

        read_only_fields = [
            "id",
            "registrado_por",
            "fecha",
        ]


class AlertaInsumoSerializer(serializers.ModelSerializer):

    insumo_nombre = serializers.CharField(
        source="insumo.nombre",
        read_only=True
    )

    orden_numero = serializers.CharField(
        source="orden_trabajo.numero",
        read_only=True,
        allow_null=True
    )

    registrado_por_nombre = serializers.CharField(
        source="registrado_por.username",
        read_only=True
    )

    estado_display = serializers.CharField(
        source="get_estado_display",
        read_only=True
    )

    class Meta:
        model = AlertaInsumo
        fields = [
            "id",
            "insumo",
            "insumo_nombre",
            "orden_trabajo",
            "orden_numero",
            "registrado_por",
            "registrado_por_nombre",
            "cantidad_solicitada",
            "descripcion",
            "estado",
            "estado_display",
            "fecha_creacion",
            "fecha_resolucion",
            "automatica",
        ]

        read_only_fields = [
            "id",
            "registrado_por",
            "fecha_creacion",
            "fecha_resolucion",
            "automatica",
        ]
