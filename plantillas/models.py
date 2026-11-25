from django.db import models


class PlantillaProceso(models.Model):
    tipo_orden = models.ForeignKey(
        "ordenes.TipoOrden",
        on_delete=models.PROTECT,
        related_name="plantillas"
    )

    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    activa = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Plantilla de proceso"
        verbose_name_plural = "Plantillas de procesos"
        ordering = ["tipo_orden", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_orden", "nombre", "version"],
                name="unique_version_plantilla"
            )
        ]

    def __str__(self):
        return f"{self.nombre} - v{self.version}"


class PlantillaEtapa(models.Model):
    plantilla = models.ForeignKey(
        PlantillaProceso,
        on_delete=models.CASCADE,
        related_name="etapas"
    )

    area = models.ForeignKey(
        "produccion.AreaProduccion",
        on_delete=models.PROTECT,
        related_name="etapas_plantilla"
    )

    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    secuencia = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Etapa de plantilla"
        verbose_name_plural = "Etapas de plantilla"
        ordering = ["secuencia"]
        constraints = [
            models.UniqueConstraint(
                fields=["plantilla", "secuencia"],
                name="unique_secuencia_plantilla"
            )
        ]

    def __str__(self):
        return f"{self.plantilla.nombre} - {self.nombre}"


class PlantillaActividad(models.Model):
    etapa = models.ForeignKey(
        PlantillaEtapa,
        on_delete=models.CASCADE,
        related_name="actividades"
    )

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    secuencia = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Actividad de plantilla"
        verbose_name_plural = "Actividades de plantilla"
        ordering = ["secuencia"]
        constraints = [
            models.UniqueConstraint(
                fields=["etapa", "secuencia"],
                name="unique_secuencia_actividad_plantilla"
            )
        ]

    def __str__(self):
        return f"{self.etapa.nombre} - {self.nombre}"
