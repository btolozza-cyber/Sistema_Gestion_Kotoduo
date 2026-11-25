
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group


admin.site.unregister(User)


@admin.register(User)
class UsuarioAdmin(UserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "mostrar_roles",
    )

    list_filter = (
        "is_active",
        "groups",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
    )

    def mostrar_roles(self, obj):
        return ", ".join(obj.groups.values_list("name", flat=True))

    mostrar_roles.short_description = "Roles"
