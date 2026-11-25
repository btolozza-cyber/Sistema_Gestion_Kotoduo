from rest_framework import serializers
from .models import Documento


class DocumentoSerializer(serializers.ModelSerializer):
    orden_numero = serializers.CharField(
        source="orden_trabajo.numero",
        read_only=True
    )

    subido_por_nombre = serializers.CharField(
        source="subido_por.username",
        read_only=True
    )

    tipo_display = serializers.CharField(
        source="get_tipo_display",
        read_only=True
    )

    class Meta:
        model = Documento
        fields = [
            "id",
            "orden_trabajo",
            "orden_numero",
            "nombre",
            "archivo",
            "tipo",
            "tipo_display",
            "descripcion",
            "subido_por",
            "subido_por_nombre",
            "fecha_subida"
        ]

        read_only_fields = [
            "id",
            "subido_por",
            "fecha_subida"
        ]
