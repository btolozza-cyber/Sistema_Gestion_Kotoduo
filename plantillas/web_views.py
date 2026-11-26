from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from auditoria.services import registrar_evento

from .models import (
    PlantillaProceso,
    PlantillaEtapa,
    PlantillaActividad,
)

from .forms import (
    PlantillaProcesoForm,
    PlantillaEtapaForm,
    PlantillaActividadForm,
)


# ==========================================================
# PERMISOS
# ==========================================================

def puede_gestionar_plantillas(usuario):
    return (
        usuario.is_superuser
        or usuario.groups.filter(
            name__in=["Administrador", "Supervisor de producción"]
        ).exists()
    )


def verificar_permiso(usuario):
    if not puede_gestionar_plantillas(usuario):
        raise PermissionDenied(
            "No tienes permisos para gestionar plantillas."
        )


# ==========================================================
# LISTADO DE PLANTILLAS
# ==========================================================

@login_required
def plantillas_lista(request):
    verificar_permiso(request.user)

    plantillas = PlantillaProceso.objects.select_related(
        "tipo_orden"
    ).prefetch_related(
        "etapas"
    ).order_by(
        "tipo_orden__nombre",
        "nombre",
        "-version"
    )

    busqueda = request.GET.get("q", "").strip()

    if busqueda:
        plantillas = plantillas.filter(
            nombre__icontains=busqueda
        ) | plantillas.filter(
            tipo_orden__nombre__icontains=busqueda
        )

    contexto = {
        "plantillas": plantillas,
        "busqueda": busqueda,
        "total_plantillas": plantillas.count(),
        "plantillas_activas": plantillas.filter(activa=True).count(),
        "plantillas_inactivas": plantillas.filter(activa=False).count(),
    }

    return render(
        request,
        "plantillas/lista.html",
        contexto
    )


# ==========================================================
# CREAR PLANTILLA
# ==========================================================

@login_required
def plantilla_crear(request):
    verificar_permiso(request.user)

    if request.method == "POST":
        formulario = PlantillaProcesoForm(request.POST)

        if formulario.is_valid():
            with transaction.atomic():
                plantilla = formulario.save()

                registrar_evento(
                    usuario=request.user,
                    modulo="plantillas",
                    accion="creacion",
                    descripcion=(
                        f"Se creó la plantilla "
                        f"'{plantilla.nombre}', versión {plantilla.version}."
                    ),
                    objeto_id=plantilla.id,
                    objeto_referencia=plantilla.nombre
                )

            return redirect(
                "plantillas:detalle",
                pk=plantilla.pk
            )

    else:
        formulario = PlantillaProcesoForm()

    return render(
        request,
        "plantillas/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Nueva plantilla",
            "texto_boton": "Crear plantilla",
        }
    )


# ==========================================================
# DETALLE DE PLANTILLA
# ==========================================================

@login_required
def plantilla_detalle(request, pk):
    verificar_permiso(request.user)

    plantilla = get_object_or_404(
        PlantillaProceso.objects.select_related(
            "tipo_orden"
        ).prefetch_related(
            "etapas__area",
            "etapas__actividades"
        ),
        pk=pk
    )

    return render(
        request,
        "plantillas/detalle.html",
        {
            "plantilla": plantilla,
            "etapas": plantilla.etapas.all().order_by("secuencia"),
        }
    )


# ==========================================================
# EDITAR PLANTILLA
# ==========================================================

@login_required
def plantilla_editar(request, pk):
    verificar_permiso(request.user)

    plantilla = get_object_or_404(
        PlantillaProceso,
        pk=pk
    )

    if request.method == "POST":
        formulario = PlantillaProcesoForm(
            request.POST,
            instance=plantilla
        )

        if formulario.is_valid():
            with transaction.atomic():
                plantilla = formulario.save()

                registrar_evento(
                    usuario=request.user,
                    modulo="plantillas",
                    accion="modificacion",
                    descripcion=(
                        f"Se modificó la plantilla '{plantilla.nombre}'."
                    ),
                    objeto_id=plantilla.id,
                    objeto_referencia=plantilla.nombre
                )

            return redirect(
                "plantillas:detalle",
                pk=plantilla.pk
            )

    else:
        formulario = PlantillaProcesoForm(
            instance=plantilla
        )

    return render(
        request,
        "plantillas/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Editar plantilla",
            "texto_boton": "Guardar cambios",
            "plantilla": plantilla,
        }
    )


# ==========================================================
# ACTIVAR / DESACTIVAR PLANTILLA
# ==========================================================

@login_required
@require_POST
def plantilla_cambiar_estado(request, pk):
    verificar_permiso(request.user)

    plantilla = get_object_or_404(
        PlantillaProceso,
        pk=pk
    )

    with transaction.atomic():
        plantilla.activa = not plantilla.activa
        plantilla.save(update_fields=["activa"])

        accion = (
            "activacion"
            if plantilla.activa
            else "desactivacion"
        )

        registrar_evento(
            usuario=request.user,
            modulo="plantillas",
            accion=accion,
            descripcion=(
                f"Se {'activó' if plantilla.activa else 'desactivó'} "
                f"la plantilla '{plantilla.nombre}'."
            ),
            objeto_id=plantilla.id,
            objeto_referencia=plantilla.nombre
        )

    return redirect(
        "plantillas:detalle",
        pk=plantilla.pk
    )


# ==========================================================
# CREAR ETAPA DE PLANTILLA
# ==========================================================

@login_required
def plantilla_etapa_crear(request, plantilla_pk):
    verificar_permiso(request.user)

    plantilla = get_object_or_404(
        PlantillaProceso,
        pk=plantilla_pk
    )

    if request.method == "POST":
        formulario = PlantillaEtapaForm(request.POST)

        if formulario.is_valid():
            with transaction.atomic():
                etapa = formulario.save(commit=False)
                etapa.plantilla = plantilla
                etapa.save()

                registrar_evento(
                    usuario=request.user,
                    modulo="plantillas",
                    accion="creacion",
                    descripcion=(
                        f"Se agregó la etapa '{etapa.nombre}' "
                        f"a la plantilla '{plantilla.nombre}'."
                    ),
                    objeto_id=etapa.id,
                    objeto_referencia=plantilla.nombre
                )

            return redirect(
                "plantillas:detalle",
                pk=plantilla.pk
            )

    else:
        siguiente_secuencia = (
            plantilla.etapas.count() + 1
        )

        formulario = PlantillaEtapaForm(
            initial={
                "secuencia": siguiente_secuencia
            }
        )

    return render(
        request,
        "plantillas/formulario_etapa.html",
        {
            "formulario": formulario,
            "plantilla": plantilla,
            "titulo": "Nueva etapa",
            "texto_boton": "Agregar etapa",
        }
    )


# ==========================================================
# EDITAR ETAPA DE PLANTILLA
# ==========================================================

@login_required
def plantilla_etapa_editar(request, pk):
    verificar_permiso(request.user)

    etapa = get_object_or_404(
        PlantillaEtapa.objects.select_related("plantilla"),
        pk=pk
    )

    if request.method == "POST":
        formulario = PlantillaEtapaForm(
            request.POST,
            instance=etapa
        )

        if formulario.is_valid():
            with transaction.atomic():
                etapa = formulario.save()

                registrar_evento(
                    usuario=request.user,
                    modulo="plantillas",
                    accion="modificacion",
                    descripcion=(
                        f"Se modificó la etapa '{etapa.nombre}' "
                        f"de la plantilla '{etapa.plantilla.nombre}'."
                    ),
                    objeto_id=etapa.id,
                    objeto_referencia=etapa.plantilla.nombre
                )

            return redirect(
                "plantillas:detalle",
                pk=etapa.plantilla.pk
            )

    else:
        formulario = PlantillaEtapaForm(
            instance=etapa
        )

    return render(
        request,
        "plantillas/formulario_etapa.html",
        {
            "formulario": formulario,
            "plantilla": etapa.plantilla,
            "etapa": etapa,
            "titulo": "Editar etapa",
            "texto_boton": "Guardar cambios",
        }
    )


# ==========================================================
# CREAR ACTIVIDAD DE PLANTILLA
# ==========================================================

@login_required
def plantilla_actividad_crear(request, etapa_pk):
    verificar_permiso(request.user)

    etapa = get_object_or_404(
        PlantillaEtapa.objects.select_related("plantilla"),
        pk=etapa_pk
    )

    if request.method == "POST":
        formulario = PlantillaActividadForm(request.POST)

        if formulario.is_valid():
            with transaction.atomic():
                actividad = formulario.save(commit=False)
                actividad.etapa = etapa
                actividad.save()

                registrar_evento(
                    usuario=request.user,
                    modulo="plantillas",
                    accion="creacion",
                    descripcion=(
                        f"Se agregó la actividad '{actividad.nombre}' "
                        f"a la etapa '{etapa.nombre}'."
                    ),
                    objeto_id=actividad.id,
                    objeto_referencia=etapa.plantilla.nombre
                )

            return redirect(
                "plantillas:detalle",
                pk=etapa.plantilla.pk
            )

    else:
        siguiente_secuencia = (
            etapa.actividades.count() + 1
        )

        formulario = PlantillaActividadForm(
            initial={
                "secuencia": siguiente_secuencia
            }
        )

    return render(
        request,
        "plantillas/formulario_actividad.html",
        {
            "formulario": formulario,
            "etapa": etapa,
            "plantilla": etapa.plantilla,
            "titulo": "Nueva actividad",
            "texto_boton": "Agregar actividad",
        }
    )


# ==========================================================
# EDITAR ACTIVIDAD DE PLANTILLA
# ==========================================================

@login_required
def plantilla_actividad_editar(request, pk):
    verificar_permiso(request.user)

    actividad = get_object_or_404(
        PlantillaActividad.objects.select_related(
            "etapa",
            "etapa__plantilla"
        ),
        pk=pk
    )

    if request.method == "POST":
        formulario = PlantillaActividadForm(
            request.POST,
            instance=actividad
        )

        if formulario.is_valid():
            with transaction.atomic():
                actividad = formulario.save()

                registrar_evento(
                    usuario=request.user,
                    modulo="plantillas",
                    accion="modificacion",
                    descripcion=(
                        f"Se modificó la actividad "
                        f"'{actividad.nombre}' de la etapa "
                        f"'{actividad.etapa.nombre}'."
                    ),
                    objeto_id=actividad.id,
                    objeto_referencia=actividad.etapa.plantilla.nombre
                )

            return redirect(
                "plantillas:detalle",
                pk=actividad.etapa.plantilla.pk
            )

    else:
        formulario = PlantillaActividadForm(
            instance=actividad
        )

    return render(
        request,
        "plantillas/formulario_actividad.html",
        {
            "formulario": formulario,
            "actividad": actividad,
            "etapa": actividad.etapa,
            "plantilla": actividad.etapa.plantilla,
            "titulo": "Editar actividad",
            "texto_boton": "Guardar cambios",
        }
    )
