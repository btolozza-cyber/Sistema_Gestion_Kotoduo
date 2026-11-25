from django.contrib import admin
from .models import PlantillaProceso, PlantillaEtapa


class PlantillaEtapaInline(admin.TabularInline):
    model = PlantillaEtapa
    extra = 1


@admin.register(PlantillaProceso)
class PlantillaProcesoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "tipo_orden",
        "version",
        "activa",
        "fecha_creacion",
    )
    list_filter = ("activa", "tipo_orden")
    search_fields = ("nombre",)
    inlines = [PlantillaEtapaInline]


@admin.register(PlantillaEtapa)
class PlantillaEtapaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "plantilla",
        "area",
        "secuencia",
    )
    list_filter = ("area",)
    search_fields = ("nombre", "plantilla__nombre")
