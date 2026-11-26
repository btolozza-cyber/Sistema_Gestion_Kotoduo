from django.contrib import admin
from .models import Documento


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nombre",
        "tipo",
        "subido_por",
        "fecha_subida",
    )

    list_filter = (
        "tipo",
        "fecha_subida",
    )

    search_fields = (
        "nombre",
        "descripcion",
        "subido_por__username",
    )

    readonly_fields = (
        "subido_por",
        "fecha_subida",
    )