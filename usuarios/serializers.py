from django.contrib.auth.models import User, Group
from rest_framework import serializers

ROLES_PERMITIDOS = [
    "Administrador",
    "Supervisor de producción",
    "Operario",
]


class UsuarioSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=8
    )

    rol = serializers.ChoiceField(
        choices=[(rol, rol) for rol in ROLES_PERMITIDOS],
        write_only=True
    )

    nombre_rol = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "rol",
            "nombre_rol",
        ]

    def get_nombre_rol(self, obj):
        grupo = obj.groups.first()
        return grupo.name if grupo else None

    def create(self, validated_data):
        rol_nombre = validated_data.pop("rol")
        password = validated_data.pop("password", None)

        if not password:
            raise serializers.ValidationError({
                "password": "La contraseña es obligatoria."
            })

        usuario = User(**validated_data)
        usuario.set_password(password)
        usuario.save()

        grupo = Group.objects.get(name=rol_nombre)
        usuario.groups.set([grupo])

        return usuario

    def update(self, instance, validated_data):
        rol_nombre = validated_data.pop("rol", None)
        password = validated_data.pop("password", None)

        for atributo, valor in validated_data.items():
            setattr(instance, atributo, valor)

        if password:
            instance.set_password(password)

        instance.save()

        if rol_nombre:
            grupo = Group.objects.get(name=rol_nombre)
            instance.groups.set([grupo])

        return instance