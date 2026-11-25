
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Insumo(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    unidad_medida = models.CharField(max_length=30)

    stock_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )

    stock_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )

    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo


class MovimientoInsumo(models.Model):

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="movimientos"
    )

    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices
    )

    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    orden_trabajo = models.ForeignKey(
        "ordenes.OrdenTrabajo",
        on_delete=models.PROTECT,
        related_name="movimientos_insumos",
        null=True,
        blank=True
    )

    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimientos_insumos"
    )

    descripcion = models.TextField(blank=True)

    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de insumo"
        verbose_name_plural = "Movimientos de insumos"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["tipo"]),
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):
        return f"{self.insumo.nombre} - {self.get_tipo_display()}"


class AlertaInsumo(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_GESTION = "en_gestion", "En gestión"
        RESUELTA = "resuelta", "Resuelta"

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="alertas"
    )

    orden_trabajo = models.ForeignKey(
        "ordenes.OrdenTrabajo",
        on_delete=models.PROTECT,
        related_name="alertas_insumos",
        null=True,
        blank=True
    )

    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="alertas_registradas"
    )

    cantidad_solicitada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    descripcion = models.TextField(blank=True)
    automatica = models.BooleanField(default=False)

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Alerta de insumo"
        verbose_name_plural = "Alertas de insumos"
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=["estado"]),
            models.Index(fields=["fecha_creacion"]),
        ]

    def __str__(self):
        return f"{self.insumo.nombre} - {self.get_estado_display()}"
