
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Configura los roles de Kotoduo."

    def handle(self, *args, **options):

        permisos_por_rol = {

            # ==================================================
            # ADMINISTRADOR
            # ==================================================

            "Administrador": {

                "ordenes": {
                    "tipoorden": [
                        "add", "view", "change", "delete"
                    ],
                    "ordentrabajo": [
                        "add", "view", "change", "delete"
                    ],
                },

                "produccion": {
                    "areaproduccion": [
                        "add", "view", "change", "delete"
                    ],
                    "etapaproduccion": [
                        "add", "view", "change", "delete"
                    ],
                    "actividad": [
                        "add", "view", "change", "delete"
                    ],
                    "historialetapa": ["view"],
                    "historialactividad": ["view"],
                },

                "alertas": {
                    "insumo": [
                        "add", "view", "change", "delete"
                    ],
                    "alertainsumo": [
                        "add", "view", "change", "delete"
                    ],
                },

                "plantillas": {
                    "plantillaproceso": [
                        "add", "view", "change", "delete"
                    ],
                    "plantillaetapa": [
                        "add", "view", "change", "delete"
                    ],
                },

                "documentos": {
                    "documento": [
                        "add", "view", "change", "delete"
                    ],
                },
            },

            # ==================================================
            # SUPERVISOR DE PRODUCCIÓN
            # ==================================================

            "Supervisor de producción": {

                "ordenes": {
                    "tipoorden": ["view"],
                    "ordentrabajo": [
                        "add", "view", "change"
                    ],
                },

                "produccion": {
                    "areaproduccion": ["view"],
                    "etapaproduccion": [
                        "add", "view", "change"
                    ],
                    "actividad": [
                        "add", "view", "change"
                    ],
                    "historialetapa": ["view"],
                    "historialactividad": ["view"],
                },

                "alertas": {
                    "insumo": [
                        "add", "view", "change"
                    ],
                    "alertainsumo": [
                        "add", "view", "change"
                    ],
                },

                "plantillas": {
                    "plantillaproceso": [
                        "add", "view", "change"
                    ],
                    "plantillaetapa": [
                        "add", "view", "change"
                    ],
                },

                "documentos": {
                    "documento": [
                        "add", "view", "change"
                    ],
                },
            },

            # ==================================================
            # OPERARIO
            # ==================================================

            "Operario": {

                "ordenes": {
                    "tipoorden": ["view"],
                    "ordentrabajo": ["view"],
                },

                "produccion": {
                    "areaproduccion": ["view"],
                    "etapaproduccion": ["view"],
                    "actividad": ["view"],
                    "historialetapa": ["view"],
                    "historialactividad": ["view"],
                },

                "alertas": {
                    "insumo": ["view"],
                    "alertainsumo": ["add", "view"],
                },

                "plantillas": {
                    "plantillaproceso": ["view"],
                    "plantillaetapa": ["view"],
                },

                "documentos": {
                    "documento": ["view"],
                },
            },
        }

        # ======================================================
        # CREACIÓN Y ACTUALIZACIÓN DE GRUPOS Y PERMISOS
        # ======================================================

        for nombre_rol, aplicaciones in permisos_por_rol.items():

            grupo, creado = Group.objects.get_or_create(
                name=nombre_rol
            )

            permisos = []

            for app, modelos in aplicaciones.items():

                for modelo, acciones in modelos.items():

                    for accion in acciones:

                        codigo = f"{accion}_{modelo}"

                        permiso = Permission.objects.get(
                            content_type__app_label=app,
                            codename=codigo,
                        )

                        permisos.append(permiso)

            grupo.permissions.set(permisos)

            estado = "creado" if creado else "actualizado"

            self.stdout.write(
                self.style.SUCCESS(
                    f"Rol {nombre_rol}: {estado} correctamente."
                )
            )
