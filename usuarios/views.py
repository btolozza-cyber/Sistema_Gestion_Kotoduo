from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.response import Response

from .serializers import UsuarioSerializer
from .forms import UsuarioForm

from ordenes.models import OrdenTrabajo
from produccion.models import EtapaProduccion
from alertas.models import Insumo, AlertaInsumo
from auditoria.models import RegistroAuditoria
from auditoria.services import registrar_evento


def es_administrador(usuario):
    return (
        usuario.is_authenticated
        and (
            usuario.is_superuser
            or usuario.groups.filter(
                name="Administrador"
            ).exists()
        )
    )


def puede_ver_auditoria(usuario):
    return (
        es_administrador(usuario)
        or usuario.groups.filter(
            name="Supervisor de producción"
        ).exists()
    )


def verificar_administrador(usuario):
    if not es_administrador(usuario):
        raise PermissionDenied(
            "No tienes permisos para administrar usuarios."
        )


class IniciarSesionView(LoginView):
    template_name = "usuarios/login.html"
    redirect_authenticated_user = False

    def get_success_url(self):
        return reverse_lazy("usuarios:dashboard")


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not es_administrador(self.request.user):
            raise DRFPermissionDenied(
                "Solo un administrador puede consultar usuarios."
            )

        return User.objects.filter(
            is_superuser=False
        ).order_by("id")

    @transaction.atomic
    def perform_create(self, serializer):
        usuario = self.request.user

        if not es_administrador(usuario):
            raise DRFPermissionDenied(
                "Solo un administrador puede crear usuarios."
            )

        nuevo_usuario = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="usuarios",
            accion="creacion",
            descripcion=(
                f"Creó el usuario '{nuevo_usuario.username}'."
            ),
            objeto_id=nuevo_usuario.id,
            objeto_referencia=nuevo_usuario.username
        )

    @transaction.atomic
    def perform_update(self, serializer):
        usuario = self.request.user

        if not es_administrador(usuario):
            raise DRFPermissionDenied(
                "Solo un administrador puede modificar usuarios."
            )

        usuario_modificado = serializer.save()

        registrar_evento(
            usuario=usuario,
            modulo="usuarios",
            accion="modificacion",
            descripcion=(
                f"Modificó los datos del usuario "
                f"'{usuario_modificado.username}'."
            ),
            objeto_id=usuario_modificado.id,
            objeto_referencia=usuario_modificado.username
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        usuario = request.user

        if not es_administrador(usuario):
            raise DRFPermissionDenied(
                "Solo un administrador puede desactivar usuarios."
            )

        usuario_objetivo = self.get_object()

        if usuario_objetivo.pk == usuario.pk:
            raise DRFPermissionDenied(
                "No puedes desactivar tu propia cuenta."
            )

        usuario_objetivo.is_active = False
        usuario_objetivo.save(update_fields=["is_active"])

        registrar_evento(
            usuario=usuario,
            modulo="usuarios",
            accion="desactivacion",
            descripcion=(
                f"Desactivó el usuario "
                f"'{usuario_objetivo.username}'."
            ),
            objeto_id=usuario_objetivo.id,
            objeto_referencia=usuario_objetivo.username
        )

        return Response({
            "mensaje": "Usuario desactivado correctamente."
        })


# =====================================================
# GESTIÓN WEB DE USUARIOS
# =====================================================

@login_required
def usuarios_lista(request):
    verificar_administrador(request.user)

    usuarios = User.objects.filter(
        is_superuser=False
    ).order_by("id")

    busqueda = request.GET.get("buscar", "").strip()
    estado = request.GET.get("estado", "")

    if busqueda:
        usuarios = usuarios.filter(
            username__icontains=busqueda
        ) | usuarios.filter(
            first_name__icontains=busqueda
        ) | usuarios.filter(
            last_name__icontains=busqueda
        ) | usuarios.filter(
            email__icontains=busqueda
        )

    if estado == "activos":
        usuarios = usuarios.filter(is_active=True)
    elif estado == "inactivos":
        usuarios = usuarios.filter(is_active=False)

    paginator = Paginator(usuarios.distinct(), 10)
    pagina = paginator.get_page(request.GET.get("page"))

    contexto = {
        "usuarios": pagina,
        "buscar": busqueda,
        "estado": estado,
        "total_usuarios": User.objects.filter(
            is_superuser=False
        ).count(),
        "usuarios_activos": User.objects.filter(
            is_superuser=False,
            is_active=True
        ).count(),
        "usuarios_inactivos": User.objects.filter(
            is_superuser=False,
            is_active=False
        ).count(),
    }

    return render(
        request,
        "usuarios/usu_lista.html",
        contexto
    )


@login_required
@transaction.atomic
def usuario_crear(request):
    verificar_administrador(request.user)

    if request.method == "POST":
        formulario = UsuarioForm(request.POST)

        if formulario.is_valid():
            nuevo_usuario = formulario.save()

            registrar_evento(
                usuario=request.user,
                modulo="usuarios",
                accion="creacion",
                descripcion=(
                    f"Creó el usuario '{nuevo_usuario.username}'."
                ),
                objeto_id=nuevo_usuario.id,
                objeto_referencia=nuevo_usuario.username
            )

            messages.success(
                request,
                "Usuario creado correctamente."
            )

            return redirect("usuarios:lista")

    else:
        formulario = UsuarioForm()

    return render(
        request,
        "usuarios/usu_form.html",
        {
            "formulario": formulario,
            "titulo": "Crear usuario",
            "modo_edicion": False,
        }
    )


@login_required
@transaction.atomic
def usuario_editar(request, pk):
    verificar_administrador(request.user)

    usuario_objetivo = get_object_or_404(
        User,
        pk=pk,
        is_superuser=False
    )

    if request.method == "POST":
        formulario = UsuarioForm(
            request.POST,
            instance=usuario_objetivo
        )

        if formulario.is_valid():
            usuario_modificado = formulario.save()

            registrar_evento(
                usuario=request.user,
                modulo="usuarios",
                accion="modificacion",
                descripcion=(
                    f"Modificó los datos del usuario "
                    f"'{usuario_modificado.username}'."
                ),
                objeto_id=usuario_modificado.id,
                objeto_referencia=usuario_modificado.username
            )

            messages.success(
                request,
                "Usuario actualizado correctamente."
            )

            return redirect(
                "usuarios:detalle",
                pk=usuario_modificado.pk
            )

    else:
        formulario = UsuarioForm(
            instance=usuario_objetivo
        )

    return render(
        request,
        "usuarios/usu_form.html",
        {
            "formulario": formulario,
            "titulo": "Editar usuario",
            "modo_edicion": True,
            "usuario_objetivo": usuario_objetivo,
        }
    )


@login_required
def usuario_detalle(request, pk):
    verificar_administrador(request.user)

    usuario_objetivo = get_object_or_404(
        User,
        pk=pk,
        is_superuser=False
    )

    grupo = usuario_objetivo.groups.first()

    return render(
        request,
        "usuarios/usu_detalle.html",
        {
            "usuario_objetivo": usuario_objetivo,
            "rol": grupo.name if grupo else "Sin rol asignado",
        }
    )


@login_required
@require_POST
@transaction.atomic
def usuario_cambiar_estado(request, pk):
    verificar_administrador(request.user)

    usuario_objetivo = get_object_or_404(
        User,
        pk=pk,
        is_superuser=False
    )

    if usuario_objetivo.pk == request.user.pk:
        messages.error(
            request,
            "No puedes desactivar tu propia cuenta."
        )
        return redirect("usuarios:detalle", pk=pk)

    usuario_objetivo.is_active = not usuario_objetivo.is_active
    usuario_objetivo.save(update_fields=["is_active"])

    if usuario_objetivo.is_active:
        accion = "reactivacion"
        mensaje = "Usuario reactivado correctamente."
        descripcion = f"Reactivó el usuario '{usuario_objetivo.username}'."
    else:
        accion = "desactivacion"
        mensaje = "Usuario desactivado correctamente."
        descripcion = f"Desactivó el usuario '{usuario_objetivo.username}'."

    registrar_evento(
        usuario=request.user,
        modulo="usuarios",
        accion=accion,
        descripcion=descripcion,
        objeto_id=usuario_objetivo.id,
        objeto_referencia=usuario_objetivo.username
    )

    messages.success(request, mensaje)

    return redirect("usuarios:detalle", pk=pk)


# =====================================================
# DASHBOARD
# =====================================================

@login_required
def dashboard(request):

    total_ordenes = OrdenTrabajo.objects.count()

    ordenes_completadas = OrdenTrabajo.objects.filter(
        estado="completada"
    ).count()

    etapas_pendientes = EtapaProduccion.objects.filter(
        estado="pendiente"
    ).count()

    etapas_en_proceso = EtapaProduccion.objects.filter(
        estado="en_proceso"
    ).count()

    etapas_completadas = EtapaProduccion.objects.filter(
        estado="completada"
    ).count()

    etapas_bloqueadas = EtapaProduccion.objects.filter(
        estado="bloqueada"
    ).count()

    total_etapas = (
        etapas_pendientes
        + etapas_en_proceso
        + etapas_completadas
        + etapas_bloqueadas
    )

    if total_etapas > 0:
        porcentaje_pendientes = round(
            etapas_pendientes / total_etapas * 100
        )
        porcentaje_en_proceso = round(
            etapas_en_proceso / total_etapas * 100
        )
        porcentaje_completadas = round(
            etapas_completadas / total_etapas * 100
        )
        porcentaje_bloqueadas = round(
            etapas_bloqueadas / total_etapas * 100
        )
    else:
        porcentaje_pendientes = 0
        porcentaje_en_proceso = 0
        porcentaje_completadas = 0
        porcentaje_bloqueadas = 0

    insumos_activos = Insumo.objects.filter(activo=True)

    total_insumos = insumos_activos.count()

    insumos_stock_bajo = insumos_activos.filter(
        stock_actual__lte=F("stock_minimo")
    ).count()

    insumos_disponibles = total_insumos - insumos_stock_bajo

    alertas_pendientes = AlertaInsumo.objects.filter(
        estado__in=["pendiente", "en_gestion"]
    ).count()

    puede_ver_actividad = puede_ver_auditoria(request.user)

    actividades_recientes = []

    if puede_ver_actividad:
        actividades_recientes = (
            RegistroAuditoria.objects
            .select_related("usuario")
            .order_by("-fecha")[:5]
        )

    contexto = {
        "total_ordenes": total_ordenes,
        "ordenes_completadas": ordenes_completadas,

        "etapas_pendientes": etapas_pendientes,
        "etapas_en_proceso": etapas_en_proceso,
        "etapas_completadas": etapas_completadas,
        "etapas_bloqueadas": etapas_bloqueadas,

        "porcentaje_pendientes": porcentaje_pendientes,
        "porcentaje_en_proceso": porcentaje_en_proceso,
        "porcentaje_completadas": porcentaje_completadas,
        "porcentaje_bloqueadas": porcentaje_bloqueadas,

        "total_insumos": total_insumos,
        "insumos_disponibles": insumos_disponibles,
        "insumos_stock_bajo": insumos_stock_bajo,
        "alertas_pendientes": alertas_pendientes,

        "puede_ver_actividad": puede_ver_actividad,
        "actividades_recientes": actividades_recientes,
    }

    return render(request, "dashboard.html", contexto)