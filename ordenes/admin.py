from django.contrib import admin
from .models import TipoOrden, OrdenTrabajo


@admin.register(TipoOrden)
class TipoOrdenAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "nombre",
        "cliente",
        "tipo",
        "estado",
        "prioridad",
        "fecha_entrega",
    )

    list_filter = ("estado", "prioridad", "tipo")
    search_fields = ("numero", "nombre", "cliente")
    readonly_fields = ("fecha_creacion",)
