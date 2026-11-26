
from django import forms
from django.contrib.auth import get_user_model

from ordenes.models import OrdenTrabajo
from .models import EtapaProduccion, Actividad, AreaProduccion


Usuario = get_user_model()


class EtapaProduccionForm(forms.ModelForm):

    class Meta:
        model = EtapaProduccion

        fields = [
            "orden_trabajo",
            "nombre",
            "area",
            "responsable",
            "descripcion",
            "secuencia",
            "estado",
        ]

        labels = {
            "orden_trabajo": "Orden de trabajo",
            "nombre": "Nombre de la etapa",
            "area": "Área de producción",
            "responsable": "Responsable",
            "descripcion": "Descripción",
            "secuencia": "Secuencia de producción",
            "estado": "Estado inicial",
        }

        widgets = {
            "orden_trabajo": forms.Select(),
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej. Confección de prendas"
            }),
            "area": forms.Select(),
            "responsable": forms.Select(),
            "descripcion": forms.Textarea(attrs={
                "placeholder": "Describe las tareas o características de esta etapa...",
                "rows": 4
            }),
            "secuencia": forms.NumberInput(attrs={
                "min": 1,
                "placeholder": "Ej. 1"
            }),
            "estado": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["orden_trabajo"].queryset = (
            OrdenTrabajo.objects.order_by("-fecha_creacion")
        )

        self.fields["area"].queryset = (
            AreaProduccion.objects.filter(activo=True)
        )

        self.fields["responsable"].queryset = (
            Usuario.objects.filter(
                is_active=True,
                groups__name="Operario"
            ).distinct().order_by("username")
        )

        self.fields["responsable"].required = False
        self.fields["descripcion"].required = False


class AsignacionEtapaForm(forms.ModelForm):

    class Meta:
        model = EtapaProduccion
        fields = ["responsable"]

        labels = {
            "responsable": "Operario responsable de la etapa",
        }

        widgets = {
            "responsable": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["responsable"].queryset = (
            Usuario.objects.filter(
                is_active=True,
                groups__name="Operario"
            ).distinct().order_by("username")
        )

        self.fields["responsable"].required = False
        self.fields["responsable"].empty_label = "Sin asignar"


class AsignacionActividadForm(forms.ModelForm):

    class Meta:
        model = Actividad
        fields = ["responsable"]

        labels = {
            "responsable": "Operario responsable de la actividad",
        }

        widgets = {
            "responsable": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["responsable"].queryset = (
            Usuario.objects.filter(
                is_active=True,
                groups__name="Operario"
            ).distinct().order_by("username")
        )

        self.fields["responsable"].required = False
        self.fields["responsable"].empty_label = "Sin asignar"
