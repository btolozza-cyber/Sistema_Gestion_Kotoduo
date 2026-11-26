from django import forms
from django.contrib.auth.models import User, Group

ROLES_PERMITIDOS = [
    "Administrador",
    "Supervisor de producción",
    "Operario",
]


class UsuarioForm(forms.ModelForm):

    rol = forms.ChoiceField(
        choices=[(rol, rol) for rol in ROLES_PERMITIDOS],
        label="Rol"
    )

    password = forms.CharField(
        label="Contraseña",
        required=False,
        min_length=8,
        widget=forms.PasswordInput(
            attrs={"placeholder": "Mínimo 8 caracteres"}
        )
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
        ]

        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
        }

        widgets = {
            "username": forms.TextInput(attrs={
                "placeholder": "Ej. usuario01"
            }),
            "first_name": forms.TextInput(attrs={
                "placeholder": "Nombre"
            }),
            "last_name": forms.TextInput(attrs={
                "placeholder": "Apellido"
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "correo@ejemplo.com"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            grupo = self.instance.groups.first()

            if grupo:
                self.fields["rol"].initial = grupo.name

            self.fields["password"].help_text = (
                "Déjala vacía para conservar la contraseña actual."
            )
        else:
            self.fields["password"].required = True

    def clean_username(self):
        username = self.cleaned_data["username"]

        usuarios = User.objects.filter(username=username)

        if self.instance and self.instance.pk:
            usuarios = usuarios.exclude(pk=self.instance.pk)

        if usuarios.exists():
            raise forms.ValidationError(
                "Este nombre de usuario ya está registrado."
            )

        return username

    def save(self, commit=True):
        usuario = super().save(commit=False)

        password = self.cleaned_data.get("password")

        if password:
            usuario.set_password(password)

        if commit:
            usuario.save()

            rol_nombre = self.cleaned_data["rol"]
            grupo = Group.objects.get(name=rol_nombre)

            usuario.groups.set([grupo])

        return usuario