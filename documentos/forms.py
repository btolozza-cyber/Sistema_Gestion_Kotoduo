
from django import forms
from .models import Documento


class DocumentoForm(forms.ModelForm):

    class Meta:
        model = Documento
        fields = [
            "nombre",
            "archivo",
            "tipo",
            "descripcion"
        ]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Nombre del documento"
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Descripción del documento"
            }),
        }
