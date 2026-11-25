from django.contrib import admin
from .models import Insumo, AlertaInsumo


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "unidad_medida", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(AlertaInsumo)
class AlertaInsumoAdmin(admin.ModelAdmin):
    list_display = (
        "insumo",
        "orden_trabajo",
        "cantidad_solicitada",
        "estado",
        "registrado_por",
        "fecha_creacion",
    )
    list_filter = ("estado", "fecha_creacion")
    search_fields = ("insumo__nombre", "orden_trabajo__numero")
    readonly_fields = ("fecha_creacion",)
