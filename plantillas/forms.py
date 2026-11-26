from django import forms

from .models import (
    PlantillaProceso,
    PlantillaEtapa,
    PlantillaActividad,
)
from ordenes.models import TipoOrden
from produccion.models import AreaProduccion


class PlantillaProcesoForm(forms.ModelForm):
    class Meta:
        model = PlantillaProceso
        fields = [
            "tipo_orden",
            "nombre",
            "descripcion",
            "version",
            "activa",
        ]
        widgets = {
            "tipo_orden": forms.Select(),
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. Fabricación de letreros",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Describe brevemente el proceso de producción.",
            }),
            "version": forms.NumberInput(attrs={
                "min": 1,
            }),
            "activa": forms.CheckboxInput(),
        }
        labels = {
            "tipo_orden": "Tipo de orden",
            "nombre": "Nombre de la plantilla",
            "descripcion": "Descripción",
            "version": "Versión",
            "activa": "Plantilla activa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["tipo_orden"].queryset = (
            TipoOrden.objects.filter(activo=True).order_by("nombre")
        )


class PlantillaEtapaForm(forms.ModelForm):
    class Meta:
        model = PlantillaEtapa
        fields = [
            "nombre",
            "descripcion",
            "area",
            "secuencia",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. Diseño y preparación",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Describe las tareas principales de esta etapa.",
            }),
            "area": forms.Select(),
            "secuencia": forms.NumberInput(attrs={
                "min": 1,
            }),
        }
        labels = {
            "nombre": "Nombre de la etapa",
            "descripcion": "Descripción",
            "area": "Área responsable",
            "secuencia": "Orden de ejecución",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["area"].queryset = (
            AreaProduccion.objects.filter(activo=True).order_by("nombre")
        )


class PlantillaActividadForm(forms.ModelForm):
    class Meta:
        model = PlantillaActividad
        fields = [
            "nombre",
            "descripcion",
            "secuencia",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. Revisar medidas del diseño",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Describe qué debe realizar el operario.",
            }),
            "secuencia": forms.NumberInput(attrs={
                "min": 1,
            }),
        }
        labels = {
            "nombre": "Nombre de la actividad",
            "descripcion": "Descripción",
            "secuencia": "Orden de ejecución",
        }
