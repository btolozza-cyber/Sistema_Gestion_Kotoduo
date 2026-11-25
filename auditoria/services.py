from .models import RegistroAuditoria


def registrar_evento(
    usuario,
    modulo,
    accion,
    descripcion,
    objeto_id=None,
    objeto_referencia=""
):
    if not usuario or not usuario.is_authenticated:
        return None

    return RegistroAuditoria.objects.create(
        usuario=usuario,
        modulo=modulo,
        accion=accion,
        descripcion=descripcion,
        objeto_id=str(objeto_id) if objeto_id is not None else "",
        objeto_referencia=objeto_referencia
    )
