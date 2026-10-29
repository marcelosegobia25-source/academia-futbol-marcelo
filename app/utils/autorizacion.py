from flask import abort, g, request, session

# Catálogo completo de permisos clasificados por módulos y funciones operativas
CATEGORIAS_PERMISOS = {
    "Alumnos y Matrícula": [
        ("ver_alumnos", "Ver alumnos", "Consultar lista de alumnos, perfiles y fichas médicas."),
        ("gestionar_alumnos", "Crear y editar alumnos", "Inscribir nuevos alumnos y actualizar sus datos."),
        ("eliminar_alumnos", "Retirar alumnos", "Dar de baja o retirar alumnos de la academia."),
        ("gestionar_becas", "Autorizar becas", "Asignar, modificar y aprobar becas a alumnos."),
    ],
    "Cobros y Mensualidades": [
        ("ver_pagos", "Ver mensualidades", "Consultar historial de pagos, estado de deudas y deudores."),
        ("registrar_pagos", "Registrar mensualidades", "Cobrar cuotas, mensualidades y emitir recibos."),
        ("anular_pagos", "Anular mensualidades", "Anular cobros y recibos erróneos."),
    ],
    "Deporte, Torneos y Asistencia": [
        ("ver_deportivo", "Ver actividad deportiva", "Consultar partidos, agenda, calendario y torneos."),
        ("gestionar_deportivo", "Gestionar partidos y torneos", "Crear fixtures, registrar resultados y podios."),
        ("gestionar_asistencia", "Registrar asistencia", "Tomar asistencia a los entrenamientos y partidos."),
        ("gestionar_equipos", "Gestionar categorías y equipos", "Administrar divisiones por edades y planteles."),
        ("gestionar_lugares", "Gestionar canchas y sedes", "Administrar canchas, predios y lugares de práctica."),
    ],
    "Seguridad y Sistema": [
        ("auditoria", "Ver auditoría", "Consultar la bitácora de auditoría y trazabilidad."),
        ("respaldos", "Crear respaldos", "Generar y descargar copias de seguridad de la base de datos."),
        ("administrar", "Administrar configuración y usuarios", "Administrar datos de la academia, usuarios y roles."),
    ],
}

# Diccionario plano de permisos (código -> nombre) para retrocompatibilidad total
PERMISOS = {codigo: nombre for grupo in CATEGORIAS_PERMISOS.values() for codigo, nombre, _ in grupo}


def cargar_usuario_actual():
    from app.models import Usuario, Rol
    from sqlalchemy.orm import joinedload
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        g.usuario_actual = None
        return None
    g.usuario_actual = (
        Usuario.query
        .options(joinedload(Usuario.rol).joinedload(Rol.permisos))
        .filter(Usuario.id_usuario == id_usuario)
        .first()
    )
    return g.usuario_actual


def tiene_permiso(codigo):
    u = getattr(g, "usuario_actual", None)
    return bool(u and u.activo and u.tiene_permiso(codigo))


def permiso_para_solicitud():
    endpoint, bp = request.endpoint or "", request.blueprint or ""
    escritura = request.method not in {"GET", "HEAD", "OPTIONS"}
    if bp in {"autenticacion", ""} or endpoint in {"index", "static"}:
        return None
    # Todo usuario autenticado puede ver el recurso de marca y cambiar su clave
    if endpoint in {"configuracion.logo", "configuracion.contrasena"}:
        return None
    if bp == "usuarios":
        return "administrar"
    if bp == "configuracion":
        return "administrar" if escritura else "ver_deportivo"
    if bp in {"categorias", "equipos"}:
        return "gestionar_equipos" if escritura else "ver_deportivo"
    if bp == "lugares":
        return "gestionar_lugares" if escritura else "ver_deportivo"
    if bp == "alumnos":
        if "eliminar" in endpoint or "retirar" in endpoint:
            return "eliminar_alumnos"
        return "gestionar_alumnos" if escritura else "ver_alumnos"
    if bp == "pagos":
        if "eliminar" in endpoint:
            return "anular_pagos"
        return "registrar_pagos" if escritura else "ver_pagos"
    if bp == "informacion":
        if "auditoria" in endpoint:
            return "auditoria"
        if "respaldo" in endpoint or "descargas" in endpoint:
            return "respaldos"
        return "administrar"
    if bp in {"partidos", "agenda", "calendario", "campeonatos"}:
        if endpoint == "calendario.asistencia" and escritura:
            return "gestionar_asistencia"
        return "gestionar_deportivo" if escritura else "ver_deportivo"
    return None
