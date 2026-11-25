from django.conf import settings
from django.db import models


class AreaProduccion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Área de producción"
        verbose_name_plural = "Áreas de producción"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class EtapaProduccion(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En proceso"
        COMPLETADA = "completada", "Completada"
        BLOQUEADA = "bloqueada", "Bloqueada"

    orden_trabajo = models.ForeignKey(
        "ordenes.OrdenTrabajo",
        on_delete=models.PROTECT,
        related_name="etapas"
    )

    area = models.ForeignKey(
        AreaProduccion,
        on_delete=models.PROTECT,
        related_name="etapas"
    )

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="etapas_asignadas",
        null=True,
        blank=True
    )

    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    secuencia = models.PositiveIntegerField()

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Etapa de producción"
        verbose_name_plural = "Etapas de producción"
        ordering = ["orden_trabajo", "secuencia"]
        constraints = [
            models.UniqueConstraint(
                fields=["orden_trabajo", "secuencia"],
                name="unique_secuencia_por_orden"
            )
        ]
        indexes = [
            models.Index(fields=["estado"]),
        ]

    def __str__(self):
        return f"{self.orden_trabajo.numero} - {self.nombre}"


class Actividad(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En_proceso"
        COMPLETADA = "completada", "Completada"

    etapa = models.ForeignKey(
        EtapaProduccion,
        on_delete=models.PROTECT,
        related_name="actividades"
    )

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="actividades_asignadas",
        null=True,
        blank=True
    )

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        ordering = ["etapa", "id"]
        indexes = [
            models.Index(fields=["estado"]),
        ]

    def __str__(self):
        return self.nombre


class HistorialEtapa(models.Model):
    etapa = models.ForeignKey(
        EtapaProduccion,
        on_delete=models.PROTECT,
        related_name="historial"
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="historiales_etapa"
    )

    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    observacion = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de etapa"
        verbose_name_plural = "Historiales de etapas"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.etapa} - {self.estado_nuevo}"


class HistorialActividad(models.Model):
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.PROTECT,
        related_name="historial"
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="historiales_actividad"
    )

    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    observacion = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de actividad"
        verbose_name_plural = "Historiales de actividades"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.actividad} - {self.estado_nuevo}"
