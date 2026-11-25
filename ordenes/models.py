from django.conf import settings
from django.db import models


class TipoOrden(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tipo de orden"
        verbose_name_plural = "Tipos de órdenes"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class OrdenTrabajo(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En proceso"
        COMPLETADA = "completada", "Completada"
        CANCELADA = "cancelada", "Cancelada"

    class Prioridad(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    numero = models.CharField(
        max_length=20,
        unique=True
    )

    nombre = models.CharField(max_length=150)

    cliente = models.CharField(max_length=150)

    descripcion = models.TextField(blank=True)

    tipo = models.ForeignKey(
        TipoOrden,
        on_delete=models.PROTECT,
        related_name="ordenes"
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    fecha_entrega = models.DateField(
        null=True,
        blank=True
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ordenes_creadas"
    )

    class Meta:
        verbose_name = "Orden de trabajo"
        verbose_name_plural = "Órdenes de trabajo"
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=["estado"]),
            models.Index(fields=["fecha_entrega"]),
        ]

    def __str__(self):
        return f"{self.numero} - {self.nombre}"
