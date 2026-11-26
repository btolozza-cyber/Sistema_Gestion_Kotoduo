
from django.conf import settings
from django.db import models


class Documento(models.Model):

    class Tipo(models.TextChoices):
        FICHA_TECNICA = "ficha_tecnica", "Ficha técnica"
        DISENO = "diseno", "Diseño"
        ESPECIFICACION = "especificacion", "Especificación"
        OTRO = "otro", "Otro"

    nombre = models.CharField(max_length=150)

    archivo = models.FileField(
        upload_to="documentos/"
    )

    tipo = models.CharField(
        max_length=30,
        choices=Tipo.choices,
        default=Tipo.OTRO
    )

    descripcion = models.TextField(blank=True)

    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documentos_subidos"
    )

    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ["-fecha_subida"]

    def __str__(self):
        return self.nombre
