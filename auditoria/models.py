from django.conf import settings
from django.db import models


class RegistroAuditoria(models.Model):

    class Modulo(models.TextChoices):
        USUARIOS = "usuarios", "Usuarios"
        ORDENES = "ordenes", "Órdenes"
        PRODUCCION = "produccion", "Producción"
        ALERTAS = "alertas", "Alertas"
        PLANTILLAS = "plantillas", "Plantillas"
        DOCUMENTOS = "documentos", "Documentos"

    class Accion(models.TextChoices):
        CREACION = "creacion", "Creación"
        MODIFICACION = "modificacion", "Modificación"
        ELIMINACION = "eliminacion", "Eliminación"
        DESACTIVACION = "desactivacion", "Desactivación"
        REACTIVACION = "reactivacion", "Reactivación"
        CAMBIO_ESTADO = "cambio_estado", "Cambio de estado"
        SUBIDA = "subida", "Subida de archivo"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registros_auditoria"
    )

    modulo = models.CharField(
        max_length=30,
        choices=Modulo.choices
    )

    accion = models.CharField(
        max_length=30,
        choices=Accion.choices
    )

    descripcion = models.TextField()

    objeto_id = models.CharField(
        max_length=100,
        blank=True
    )

    objeto_referencia = models.CharField(
        max_length=150,
        blank=True
    )

    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["modulo", "fecha"]),
            models.Index(fields=["usuario", "fecha"]),
            models.Index(fields=["accion", "fecha"]),
        ]

    def __str__(self):
        return (
            f"{self.usuario.username} - "
            f"{self.modulo} - {self.accion}"
        )
