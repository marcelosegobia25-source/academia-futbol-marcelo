from flask import abort, g, request, session

PERMISOS = {
    "ver_alumnos": "Ver alumnos", "gestionar_alumnos": "Crear y editar alumnos",
    "ver_pagos": "Ver mensualidades y caja", "registrar_pagos": "Registrar mensualidades",
    "anular_pagos": "Anular mensualidades", "cerrar_caja": "Cerrar caja", "reabrir_caja": "Reabrir caja",
    "ver_finanzas": "Ver finanzas", "gestionar_finanzas": "Gestionar finanzas",
    "gestionar_inventario": "Gestionar inventario y ventas", "ver_deportivo": "Ver actividad deportiva",
    "gestionar_deportivo": "Gestionar actividad deportiva", "auditoria": "Ver auditoría",
    "respaldos": "Crear respaldos", "administrar": "Administrar configuración y usuarios",
    "anular_ventas": "Anular ventas y devoluciones",
    "gestionar_becas": "Autorizar becas",
    "gestionar_asistencia": "Registrar asistencia",
}

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
    if bp in {"autenticacion", ""} or endpoint in {"index", "static"}: return None
    # Todo usuario autenticado debe poder ver el recurso de marca y cambiar su
    # propia clave temporal; el resto de Configuracion es solo administrativo.
    if endpoint in {"configuracion.logo", "configuracion.contrasena"}: return None
    if bp == "usuarios" or bp in {"configuracion", "categorias", "equipos", "lugares"}:
        return "administrar" if escritura or bp in {"usuarios", "configuracion"} else "ver_deportivo"
    if bp == "alumnos": return "gestionar_alumnos" if escritura else "ver_alumnos"
    if bp == "pagos":
        if "reabrir" in endpoint: return "reabrir_caja"
        if "abrir_caja" in endpoint: return "registrar_pagos"
        if "eliminar" in endpoint: return "anular_pagos"
        if "caja" in endpoint and escritura: return "cerrar_caja"
        return "registrar_pagos" if escritura else "ver_pagos"
    if bp == "informacion":
        if "auditoria" in endpoint: return "auditoria"
        if "respaldo" in endpoint or "descargas" in endpoint: return "respaldos"
        return "ver_finanzas"
    if bp == "gestion":
        if any(x in endpoint for x in ("venta_anular", "venta_devolver")): return "anular_ventas"
        if any(x in endpoint for x in ("inventario", "venta", "producto", "variante")):
            return "gestionar_inventario" if escritura else "ver_finanzas"
        return "gestionar_finanzas" if escritura else "ver_finanzas"
    if bp in {"partidos", "agenda", "calendario", "campeonatos"}:
        if endpoint == "calendario.asistencia" and escritura: return "gestionar_asistencia"
        return "gestionar_deportivo" if escritura else "ver_deportivo"
    return None
