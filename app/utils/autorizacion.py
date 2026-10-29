from flask import abort, current_app, g, request, session

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
    from app.extensions import db
    from app.models import Usuario, Rol
    from sqlalchemy.orm import joinedload
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        g.usuario_actual = None
        return None
    usuario = (
        Usuario.query
        .options(joinedload(Usuario.rol).joinedload(Rol.permisos))
        .filter(Usuario.id_usuario == id_usuario)
        .populate_existing()
        .first()
    )
    if usuario:
        try:
            db.session.refresh(usuario, ["id_rol", "rol"])
            if usuario.rol:
                db.session.refresh(usuario.rol, ["permisos"])
        except Exception:
            pass
    g.usuario_actual = usuario
    return g.usuario_actual


def tiene_permiso(codigo_o_codigos):
    if not current_app.config.get("AUTH_REQUIRED", True):
        return True
    u = getattr(g, "usuario_actual", None)
    if not u or not u.activo:
        return False
    if isinstance(codigo_o_codigos, (tuple, list, set)):
        return any(u.tiene_permiso(c) for c in codigo_o_codigos)
    return u.tiene_permiso(codigo_o_codigos)


def permiso_para_solicitud():
    endpoint = request.endpoint or ""
    bp = request.blueprint or ""
    escritura = request.method not in {"GET", "HEAD", "OPTIONS"}

    # Rutas públicas o de infraestructura general
    if bp in {"autenticacion", ""} or endpoint in {"index", "static", "health", "ping"}:
        return None

    # Autenticados: gestión de clave personal y logo
    if endpoint in {"configuracion.logo", "configuracion.contrasena"}:
        return None

    # Módulo de usuarios y roles: exclusivo administradores
    if bp == "usuarios":
        return "administrar"

    # Módulo de configuración del sistema: exclusivo administradores
    if bp == "configuracion":
        return "administrar"

    # Módulo de auditoría y respaldos
    if bp == "informacion":
        if "auditoria" in endpoint:
            return "auditoria"
        if "respaldo" in endpoint or "descargas" in endpoint:
            return "respaldos"
        if "recaudacion" in endpoint:
            return "ver_pagos"
        return "administrar"

    # Módulo de alumnos
    if bp == "alumnos":
        if endpoint == "alumnos.eliminar":
            return "eliminar_alumnos"
        if endpoint in {"alumnos.asistencias_guardar", "alumnos.convocatoria_guardar", "alumnos.convocatoria_eliminar"}:
            return "gestionar_asistencia"
        if endpoint in {"alumnos.asistencias", "alumnos.convocatoria_detalle", "alumnos.convocatoria_pdf", "alumnos.convocatoria_excel"}:
            return ("gestionar_asistencia", "ver_deportivo")
        if endpoint in {"alumnos.crear", "alumnos.editar", "alumnos.recalcular_categoria"}:
            return "gestionar_alumnos"
        return "ver_alumnos"

    # Módulo de pagos y cuotas
    if bp == "pagos":
        if endpoint == "pagos.eliminar":
            return "anular_pagos"
        if endpoint in {"pagos.crear", "pagos.cambiar_fecha_base"}:
            return "registrar_pagos"
        return "ver_pagos"

    # Módulo de categorías y equipos
    if bp in {"categorias", "equipos"}:
        if any(acc in endpoint for acc in ("crear", "editar", "eliminar")):
            return "gestionar_equipos"
        return ("gestionar_equipos", "ver_deportivo", "administrar")

    # Módulo de canchas y lugares
    if bp == "lugares":
        if any(acc in endpoint for acc in ("crear", "editar", "eliminar")):
            return "gestionar_lugares"
        return ("gestionar_lugares", "ver_deportivo", "administrar")

    # Módulo de calendario y entrenamientos
    if bp == "calendario":
        if "personal" in endpoint:
            return "administrar"
        if "asistencia" in endpoint:
            return "gestionar_asistencia" if escritura else ("gestionar_asistencia", "ver_deportivo")
        if any(acc in endpoint for acc in ("crear", "editar", "eliminar")):
            return "gestionar_deportivo"
        return "ver_deportivo"

    # Módulos deportivos: partidos, agenda, campeonatos
    if bp in {"partidos", "agenda", "campeonatos"}:
        if any(acc in endpoint for acc in ("crear", "editar", "eliminar", "resultado", "walkover", "convocatoria")):
            return "gestionar_deportivo"
        return "ver_deportivo"

    return None
