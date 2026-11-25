
from django.contrib import admin
from .models import (
    AreaProduccion,
    EtapaProduccion,
    Actividad,
    HistorialEtapa,
    HistorialActividad,
)


@admin.register(AreaProduccion)
class AreaProduccionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(EtapaProduccion)
class EtapaProduccionAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "orden_trabajo",
        "area",
        "responsable",
        "secuencia",
        "estado",
    )
    list_filter = ("estado", "area")
    search_fields = ("nombre", "orden_trabajo__numero")


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "etapa", "responsable", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "etapa__nombre")


@admin.register(HistorialEtapa)
class HistorialEtapaAdmin(admin.ModelAdmin):
    list_display = (
        "etapa",
        "usuario",
        "estado_anterior",
        "estado_nuevo",
        "fecha",
    )
    readonly_fields = ("fecha",)


@admin.register(HistorialActividad)
class HistorialActividadAdmin(admin.ModelAdmin):
    list_display = (
        "actividad",
        "usuario",
        "estado_anterior",
        "estado_nuevo",
        "fecha",
    )
    readonly_fields = ("fecha",)
