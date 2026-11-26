import os

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render
)
from django.views.decorators.http import require_POST

from rest_framework import viewsets
from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
    IsAuthenticated
)
from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
    JSONParser
)

from .models import Documento
from .forms import DocumentoForm
from .serializers import DocumentoSerializer

from auditoria.services import registrar_evento


# PERMISOS

def es_gestor_documentos(user):
    return (
        user.is_superuser
        or user.groups.filter(
            name__in=[
                "Administrador",
                "Supervisor de producción"
            ]
        ).exists()
    )


def es_usuario_documentos(user):
    return (
        es_gestor_documentos(user)
        or user.groups.filter(name="Operario").exists()
    )


def verificar_acceso(user):
    if not es_usuario_documentos(user):
        raise PermissionDenied


# API REST

class PermisoDocumento(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if es_gestor_documentos(user):
            return True

        if user.groups.filter(name="Operario").exists():
            return request.method in SAFE_METHODS

        return False


class DocumentoViewSet(viewsets.ModelViewSet):

    serializer_class = DocumentoSerializer

    permission_classes = [
        IsAuthenticated,
        PermisoDocumento
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser
    ]

    queryset = Documento.objects.select_related(
        "subido_por"
    )

    def get_queryset(self):
        user = self.request.user

        if es_usuario_documentos(user):
            return self.queryset

        return self.queryset.none()

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user

        documento = serializer.save(
            subido_por=usuario
        )

        registrar_evento(
            usuario=usuario,
            modulo="documentos",
            accion="subida",
            descripcion=(
                f"Subió el documento '{documento.nombre}'."
            ),
            objeto_id=documento.id,
            objeto_referencia=documento.nombre
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        usuario = self.request.user

        registrar_evento(
            usuario=usuario,
            modulo="documentos",
            accion="eliminacion",
            descripcion=(
                f"Eliminó el documento '{instance.nombre}'."
            ),
            objeto_id=instance.id,
            objeto_referencia=instance.nombre
        )

        if instance.archivo:
            instance.archivo.delete(save=False)

        instance.delete()


# INTERFAZ WEB

@login_required
def documentos_lista(request):
    verificar_acceso(request.user)

    documentos = Documento.objects.select_related(
        "subido_por"
    ).all()

    return render(
        request,
        "documentos/doc_lista.html",
        {
            "documentos": documentos,
            "puede_gestionar": es_gestor_documentos(request.user)
        }
    )


@login_required
def documento_subir(request):
    verificar_acceso(request.user)

    if not es_gestor_documentos(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = DocumentoForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            with transaction.atomic():
                documento = form.save(commit=False)
                documento.subido_por = request.user
                documento.save()

                registrar_evento(
                    usuario=request.user,
                    modulo="documentos",
                    accion="subida",
                    descripcion=(
                        f"Subió el documento '{documento.nombre}'."
                    ),
                    objeto_id=documento.id,
                    objeto_referencia=documento.nombre
                )

            return redirect("documentos:lista")

    else:
        form = DocumentoForm()

    return render(
        request,
        "documentos/doc_form.html",
        {
            "form": form,
            "titulo": "Subir documento"
        }
    )


@login_required
def documento_detalle(request, pk):
    verificar_acceso(request.user)

    documento = get_object_or_404(
        Documento.objects.select_related("subido_por"),
        pk=pk
    )

    return render(
        request,
        "documentos/doc_detalle.html",
        {
            "documento": documento,
            "puede_gestionar": es_gestor_documentos(request.user)
        }
    )


@login_required
def documento_descargar(request, pk):
    verificar_acceso(request.user)

    documento = get_object_or_404(
        Documento,
        pk=pk
    )

    if not documento.archivo:
        raise PermissionDenied

    return FileResponse(
        documento.archivo.open("rb"),
        as_attachment=True,
        filename=os.path.basename(documento.archivo.name)
    )


@login_required
@require_POST
def documento_eliminar(request, pk):
    verificar_acceso(request.user)

    if not es_gestor_documentos(request.user):
        raise PermissionDenied

    documento = get_object_or_404(
        Documento,
        pk=pk
    )

    with transaction.atomic():
        registrar_evento(
            usuario=request.user,
            modulo="documentos",
            accion="eliminacion",
            descripcion=(
                f"Eliminó el documento '{documento.nombre}'."
            ),
            objeto_id=documento.id,
            objeto_referencia=documento.nombre
        )

        if documento.archivo:
            documento.archivo.delete(save=False)

        documento.delete()

    return redirect("documentos:lista")
