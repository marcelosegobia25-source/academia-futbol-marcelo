import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, abort, g, render_template, redirect, request, session, url_for
from config import Config
from app.extensions import db, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.instance_path), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["BRAND_FOLDER"], exist_ok=True)
    os.makedirs(app.config["DOCUMENT_FOLDER"], exist_ok=True)
    os.makedirs(app.config["EXPORT_FOLDER"], exist_ok=True)
    os.makedirs(app.config["DOWNLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["LOG_FOLDER"], exist_ok=True)
    _migrar_fotografias_privadas(app)

    if not app.testing:
        manejador = RotatingFileHandler(
            os.path.join(app.config["LOG_FOLDER"], "academia.log"),
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        manejador.setLevel(logging.INFO)
        manejador.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(module)s: %(message)s"
        ))
        app.logger.addHandler(manejador)
        app.logger.setLevel(logging.INFO)

    from app.utils.backup import crear_respaldo_diario
    try:
        respaldo = crear_respaldo_diario(app)
        if respaldo:
            app.logger.info("Respaldo automático creado: %s", respaldo)
    except Exception:
        app.logger.exception("No se pudo crear el respaldo automático")

    db.init_app(app)
    csrf.init_app(app)

    from app.routes.alumnos import bp as alumnos_bp
    from app.routes.categorias import bp as categorias_bp
    from app.routes.equipos import bp as equipos_bp
    from app.routes.pagos import bp as pagos_bp
    from app.routes.partidos import bp as partidos_bp
    from app.routes.agenda import bp as agenda_bp
    from app.routes.calendario import bp as calendario_bp
    from app.routes.campeonatos import bp as campeonatos_bp
    from app.routes.configuracion import bp as configuracion_bp
    from app.routes.informacion import bp as informacion_bp
    from app.routes.lugares import bp as lugares_bp
    from app.routes.autenticacion import bp as autenticacion_bp
    from app.routes.gestion import bp as gestion_bp
    from app.routes.usuarios import bp as usuarios_bp

    app.register_blueprint(alumnos_bp)
    app.register_blueprint(categorias_bp)
    app.register_blueprint(equipos_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(partidos_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(calendario_bp)
    app.register_blueprint(campeonatos_bp)
    app.register_blueprint(configuracion_bp)
    app.register_blueprint(informacion_bp)
    app.register_blueprint(lugares_bp)
    app.register_blueprint(autenticacion_bp)
    app.register_blueprint(gestion_bp)
    app.register_blueprint(usuarios_bp)

    @app.context_processor
    def personalizacion_global():
        from app.models import Configuracion
        from app.utils.autorizacion import tiene_permiso
        return {"marca": Configuracion.obtener(), "usuario_actual": getattr(g, "usuario_actual", None), "puede": tiene_permiso}

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.before_request
    def asegurar_respaldo_del_dia():
        hoy = __import__("datetime").date.today().isoformat()
        if app.extensions.get("ultimo_respaldo_verificado") == hoy:
            return
        try:
            crear_respaldo_diario(app)
            app.extensions["ultimo_respaldo_verificado"] = hoy
        except Exception:
            app.logger.exception("No se pudo verificar el respaldo diario")

    @app.before_request
    def exigir_autenticacion():
        if not app.config.get("AUTH_REQUIRED", True):
            return None
        if request.endpoint in {"static", "autenticacion.login"}:
            return None
        if session.get("autenticado"):
            from app.utils.autorizacion import cargar_usuario_actual, permiso_para_solicitud, tiene_permiso
            usuario = cargar_usuario_actual()
            if usuario is None or not usuario.activo:
                session.clear()
                return redirect(url_for("autenticacion.login", next=request.full_path))
            if usuario.debe_cambiar_clave and request.endpoint not in {
                "configuracion.contrasena", "configuracion.logo",
                "autenticacion.logout", "static",
            }:
                return redirect(url_for("configuracion.contrasena"))
            requerido = permiso_para_solicitud()
            if requerido and not tiene_permiso(requerido):
                abort(403)
            return None
        return redirect(url_for("autenticacion.login", next=request.full_path))

    @app.errorhandler(404)
    def no_encontrado(error):
        return render_template("errores/404.html"), 404

    @app.errorhandler(500)
    def error_interno(error):
        db.session.rollback()
        app.logger.exception("Error interno no controlado: %s", error)
        return render_template("errores/500.html"), 500

    @app.errorhandler(403)
    def prohibido(error):
        return render_template("errores/403.html"), 403

    @app.after_request
    def encabezados_seguridad(respuesta):
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.headers.setdefault("X-Frame-Options", "DENY")
        respuesta.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        respuesta.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        respuesta.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        respuesta.headers.setdefault("Referrer-Policy", "same-origin")
        respuesta.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; font-src 'self'; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        respuesta.headers.setdefault("Cache-Control", "no-store")
        return respuesta

    with app.app_context():
        db.create_all()
        _migrar_esquema_legacy()
        from app.migrations import ejecutar_migraciones
        ejecutar_migraciones()
        _sembrar_seguridad_inicial()
        _sembrar_categorias_por_defecto()
        _sembrar_configuracion_por_defecto()
        from app.routes.gestion import generar_calendario_programado
        generar_calendario_programado()

    return app


def _migrar_fotografias_privadas(app):
    """Retira fotografías de la carpeta pública conservando nombres y datos."""
    origen = app.config.get("LEGACY_UPLOAD_FOLDER")
    destino = app.config["UPLOAD_FOLDER"]
    if not origen or not os.path.isdir(origen):
        return
    os.makedirs(destino, exist_ok=True)
    for nombre in os.listdir(origen):
        ruta_origen = os.path.join(origen, nombre)
        ruta_destino = os.path.join(destino, nombre)
        if not os.path.isfile(ruta_origen):
            continue
        if os.path.exists(ruta_destino):
            os.remove(ruta_origen)
        else:
            shutil.move(ruta_origen, ruta_destino)


def _sembrar_configuracion_por_defecto():
    from app.models import Configuracion
    Configuracion.obtener()


def _sembrar_seguridad_inicial():
    from app.models import Configuracion, Permiso, Rol, Usuario
    from app.utils.autorizacion import PERMISOS
    objetos = {}
    permisos_nuevos = set()
    for codigo, nombre in PERMISOS.items():
        permiso = Permiso.query.filter_by(codigo=codigo).first()
        if not permiso:
            permiso = Permiso(codigo=codigo, nombre=nombre)
            db.session.add(permiso)
            permisos_nuevos.add(codigo)
        objetos[codigo] = permiso
    db.session.flush()
    perfiles = {
        "Administrador": set(PERMISOS),
        "Secretaría": {"ver_alumnos", "gestionar_alumnos", "ver_pagos", "registrar_pagos", "ver_deportivo", "gestionar_deportivo", "gestionar_asistencia"},
        "Caja": {"ver_alumnos", "ver_pagos", "registrar_pagos", "cerrar_caja", "ver_finanzas", "gestionar_inventario"},
        "Profesor": {"ver_alumnos", "ver_deportivo", "gestionar_asistencia"},
    }
    roles = {}
    for nombre, codigos in perfiles.items():
        rol = Rol.query.filter_by(nombre=nombre).first()
        nuevo = rol is None
        if not rol:
            rol = Rol(nombre=nombre)
            db.session.add(rol)
        if nuevo or not rol.permisos or nombre == "Administrador":
            rol.permisos = [objetos[c] for c in codigos]
        elif permisos_nuevos:
            actuales = {permiso.codigo for permiso in rol.permisos}
            rol.permisos.extend(objetos[c] for c in (codigos & permisos_nuevos) if c not in actuales)
        roles[nombre] = rol
    db.session.flush()
    if Usuario.query.count() == 0:
        config = Configuracion.obtener()
        admin = Usuario(
            nombre_usuario="admin", nombre_completo="Administrador",
            contrasena_hash=config.contrasena_hash, rol=roles["Administrador"],
            debe_cambiar_clave=config.verificar_contrasena("00000"),
        )
        db.session.add(admin)
    db.session.commit()


def _migrar_esquema_legacy():
    """Añade columnas nuevas sin destruir la base local existente."""
    from sqlalchemy import inspect, text

    columnas_pago = {columna["name"] for columna in inspect(db.engine).get_columns("pago")}
    if "eliminado_en" not in columnas_pago:
        db.session.execute(text("ALTER TABLE pago ADD COLUMN eliminado_en DATETIME"))
        db.session.commit()

    columnas_equipo = {columna["name"] for columna in inspect(db.engine).get_columns("equipo")}
    # Los equipos pueden ser globales (id_categoria = NULL) o pertenecer a
    # una categoria concreta. En versiones anteriores esta migracion
    # reconstruia la tabla cuando la columna ya existia, eliminandola; en el
    # siguiente arranque volvia a agregarla. Ademas de alternar el esquema en
    # cada inicio, se perdia la categoria asignada a cada equipo.
    #
    # La migracion correcta es aditiva e idempotente: conservar la columna y
    # sus datos si ya existen, y agregarla solamente en bases antiguas.
    if "id_categoria" not in columnas_equipo:
        db.session.execute(text(
            "ALTER TABLE equipo ADD COLUMN id_categoria INTEGER REFERENCES categoria(id_categoria)"
        ))
        db.session.commit()


def _sembrar_categorias_por_defecto():
    """Crea categorías base si la base de datos está vacía (ajustables luego)."""
    from app.models import Categoria

    if Categoria.query.count() > 0:
        return
    base = [
        ("7", 6, 7),
        ("9", 8, 9),
        ("11", 10, 11),
        ("13", 12, 13),
        ("15", 14, 15),
        ("17", 16, 17),
        ("19", 18, 19),
        ("Ascenso", None, None),
    ]
    for nombre, e_min, e_max in base:
        db.session.add(Categoria(nombre=nombre, edad_min=e_min, edad_max=e_max))
    db.session.commit()
