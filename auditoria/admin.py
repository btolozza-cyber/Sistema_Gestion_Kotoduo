from django.contrib import admin
from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "usuario",
        "modulo",
        "accion",
        "objeto_referencia",
        "fecha",
    )

    list_filter = (
        "modulo",
        "accion",
        "fecha",
    )

    search_fields = (
        "usuario__username",
        "descripcion",
        "objeto_referencia",
    )

    readonly_fields = (
        "usuario",
        "modulo",
        "accion",
        "descripcion",
        "objeto_id",
        "objeto_referencia",
        "fecha",
    )

    ordering = ("-fecha",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
