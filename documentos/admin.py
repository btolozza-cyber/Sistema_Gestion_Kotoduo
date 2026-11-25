from django.contrib import admin
from .models import Documento


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "orden_trabajo",
        "tipo",
        "subido_por",
        "fecha_subida",
    )

    list_filter = ("tipo", "fecha_subida")
    search_fields = (
        "nombre",
        "orden_trabajo__numero",
    )

    readonly_fields = ("fecha_subida",)
