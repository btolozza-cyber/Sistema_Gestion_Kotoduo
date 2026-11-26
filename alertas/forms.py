from django import forms

from .models import Insumo, MovimientoInsumo


class InsumoForm(forms.ModelForm):

    class Meta:
        model = Insumo
        fields = [
            "nombre",
            "descripcion",
            "unidad_medida",
            "stock_minimo",
            "activo",
        ]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre del insumo",
            }),
            "descripcion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Descripción del insumo",
            }),
            "unidad_medida": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej. unidades, metros, kg",
            }),
            "stock_minimo": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
            }),
            "activo": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }


class MovimientoInsumoForm(forms.ModelForm):

    class Meta:
        model = MovimientoInsumo
        fields = [
            "insumo",
            "tipo",
            "cantidad",
            "orden_trabajo",
            "descripcion",
        ]

        widgets = {
            "insumo": forms.Select(attrs={
                "class": "form-control",
            }),
            "tipo": forms.Select(attrs={
                "class": "form-control",
            }),
            "cantidad": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
            }),
            "orden_trabajo": forms.Select(attrs={
                "class": "form-control",
            }),
            "descripcion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Descripción del movimiento",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["insumo"].queryset = Insumo.objects.filter(
            activo=True
        )

        self.fields["orden_trabajo"].required = False
        self.fields["orden_trabajo"].queryset = (
            self.fields["orden_trabajo"].queryset.order_by("-fecha_creacion")
        )
