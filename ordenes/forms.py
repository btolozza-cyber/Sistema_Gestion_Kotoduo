from django import forms

from .models import OrdenTrabajo, TipoOrden
from plantillas.models import PlantillaProceso


class OrdenTrabajoForm(forms.ModelForm):

    class Meta:
        model = OrdenTrabajo

        fields = [
            "nombre",
            "cliente",
            "descripcion",
            "tipo",
            "plantilla",
            "prioridad",
            "fecha_entrega",
        ]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. Poleras corporativas",
            }),

            "cliente": forms.TextInput(attrs={
                "placeholder": "Nombre del cliente",
            }),

            "descripcion": forms.Textarea(attrs={
                "placeholder": "Describe los detalles del trabajo...",
                "rows": 4,
            }),

            "tipo": forms.Select(),

            "plantilla": forms.Select(),

            "prioridad": forms.Select(),

            "fecha_entrega": forms.DateInput(attrs={
                "type": "date",
            }),
        }

        labels = {
            "nombre": "Nombre del trabajo",
            "cliente": "Cliente",
            "descripcion": "Descripción del trabajo",
            "tipo": "Tipo de orden",
            "plantilla": "Plantilla de producción",
            "prioridad": "Prioridad",
            "fecha_entrega": "Fecha de entrega",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["tipo"].queryset = TipoOrden.objects.filter(
            activo=True
        ).order_by("nombre")

        self.fields["plantilla"].queryset = PlantillaProceso.objects.filter(
            activa=True
        ).select_related(
            "tipo_orden"
        ).order_by(
            "tipo_orden__nombre",
            "nombre"
        )

        self.fields["plantilla"].required = False

        self.fields["plantilla"].empty_label = "Seleccionar plantilla"

        self.fields["plantilla"].help_text = (
            "Selecciona una plantilla correspondiente al tipo de orden."
        )

        self.fields["fecha_entrega"].required = False

    def clean(self):
        cleaned_data = super().clean()

        tipo = cleaned_data.get("tipo")
        plantilla = cleaned_data.get("plantilla")

        if tipo and plantilla:
            if plantilla.tipo_orden_id != tipo.id:
                self.add_error(
                    "plantilla",
                    "La plantilla seleccionada no corresponde al tipo de orden."
                )

        elif tipo and not plantilla:
            existen_plantillas = PlantillaProceso.objects.filter(
                tipo_orden=tipo,
                activa=True
            ).exists()

            if existen_plantillas:
                self.add_error(
                    "plantilla",
                    "Debes seleccionar una plantilla para este tipo de orden."
                )

        return cleaned_data
