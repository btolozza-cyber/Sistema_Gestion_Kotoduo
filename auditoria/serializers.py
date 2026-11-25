from rest_framework import serializers
from .models import RegistroAuditoria


class RegistroAuditoriaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source="usuario.username",
        read_only=True
    )

    modulo_display = serializers.CharField(
        source="get_modulo_display",
        read_only=True
    )

    accion_display = serializers.CharField(
        source="get_accion_display",
        read_only=True
    )

    class Meta:
        model = RegistroAuditoria
        fields = [
            "id",
            "usuario",
            "usuario_nombre",
            "modulo",
            "modulo_display",
            "accion",
            "accion_display",
            "descripcion",
            "objeto_id",
            "objeto_referencia",
            "fecha"
        ]

        read_only_fields = fields
