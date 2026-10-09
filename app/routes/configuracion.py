import re
import os
import uuid
from datetime import date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, abort
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Configuracion, Auditoria, Tarifa
from app.utils.validacion import (
    ErrorValidacion, decimal_positivo, texto_requerido, texto_opcional, entero, opcion
)

bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")


@bp.route("/")
def panel():
    config = Configuracion.obtener()
    return render_template("configuracion/panel.html", config=config)


@bp.route("/mensualidad", methods=["GET", "POST"])
def mensualidad():
    config = Configuracion.obtener()
    if request.method == "POST":
        monto_anterior = config.monto_mensualidad
        try:
            config.monto_mensualidad = decimal_positivo(
                request.form.get("monto_mensualidad"), "Monto de mensualidad", 100000
            ) or 0
            config.nombre_academia = texto_requerido(
                request.form.get("nombre_academia"), "Nombre de la academia", 150
            )
            config.telefono = texto_opcional(request.form.get("telefono"), "Teléfono", 50)
            config.direccion = texto_opcional(request.form.get("direccion"), "Dirección", 255)
            config.moneda = opcion(
                request.form.get("moneda", "BOB"), ["BOB", "USD"], "Moneda"
            )
            config.dias_proximo_vencimiento = entero(
                request.form.get("dias_proximo_vencimiento"), "Días de aviso",
                1, 30, requerido=True,
            )
            config.marcador_walkover = entero(
                request.form.get("marcador_walkover"), "Marcador walkover",
                1, 20, requerido=True,
            )
            config.gestion_ficha = entero(
                request.form.get("gestion_ficha"), "Gestión de la ficha",
                2000, 2100, requerido=True,
            )
            config.eslogan = texto_opcional(request.form.get("eslogan"), "Eslogan", 180)
            for campo, etiqueta in (
                ("color_primario", "Color principal"),
                ("color_secundario", "Color secundario"),
                ("color_acento", "Color de acento"),
            ):
                valor = request.form.get(campo, "").strip()
                if not re.fullmatch(r"#[0-9a-fA-F]{6}", valor):
                    raise ErrorValidacion(f"{etiqueta} no es válido.")
                setattr(config, campo, valor.lower())
            logo = request.files.get("logo")
            if logo and logo.filename:
                extension = secure_filename(logo.filename).rsplit(".", 1)[-1].lower()
                if extension not in current_app.config["ALLOWED_PHOTO_EXT"]:
                    raise ErrorValidacion("El logo debe ser PNG, JPG, JPEG o WEBP.")
                nombre = f"logo_{uuid.uuid4().hex}.{extension}"
                logo.save(os.path.join(current_app.config["BRAND_FOLDER"], nombre))
                anterior = config.logo
                config.logo = nombre
                if anterior:
                    ruta_anterior = os.path.join(current_app.config["BRAND_FOLDER"], anterior)
                    if os.path.isfile(ruta_anterior):
                        os.remove(ruta_anterior)
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template("configuracion/mensualidad.html", config=config)
        db.session.add(Auditoria(
            modulo="Configuración", accion="Actualizar",
            entidad="Configuracion", id_entidad=config.id,
            detalle=(
                f"monto={config.monto_mensualidad}; moneda={config.moneda}; "
                f"gestion_ficha={config.gestion_ficha}"
            ),
        ))
        if config.monto_mensualidad != monto_anterior:
            vigente = Tarifa.query.filter_by(concepto="Mensualidad", activo=True).order_by(Tarifa.fecha_inicio.desc()).first()
            if vigente:
                vigente.activo = False
                vigente.fecha_fin = date.today() - timedelta(days=1)
            db.session.add(Tarifa(
                concepto="Mensualidad", monto=config.monto_mensualidad,
                fecha_inicio=date.today(), activo=True,
            ))
        db.session.commit()
        flash("Monto de mensualidad actualizado.", "success")
        return redirect(url_for("configuracion.panel"))
    return render_template("configuracion/mensualidad.html", config=config)


@bp.route("/logo")
def logo():
    config = Configuracion.obtener()
    if not config.logo:
        abort(404)
    ruta = os.path.join(current_app.config["BRAND_FOLDER"], config.logo)
    if not os.path.isfile(ruta):
        abort(404)
    return send_file(ruta, max_age=0)


@bp.route("/contrasena", methods=["GET", "POST"])
def contrasena():
    config = Configuracion.obtener()
    from flask import g
    usuario = getattr(g, "usuario_actual", None)
    if request.method == "POST":
        actual = request.form.get("contrasena_actual", "")
        nueva = request.form.get("contrasena_nueva", "")
        confirmacion = request.form.get("confirmar_contrasena", "")
        if not usuario or not usuario.verificar_contrasena(actual):
            flash("La contraseña actual no es correcta.", "danger")
        elif not re.fullmatch(r"\d{5}", nueva):
            flash("La nueva contraseña debe contener exactamente 5 números.", "danger")
        elif nueva != confirmacion:
            flash("La confirmación no coincide con la nueva contraseña.", "danger")
        elif nueva == actual:
            flash("La nueva contraseña debe ser diferente de la actual.", "danger")
        else:
            usuario.establecer_contrasena(nueva)
            usuario.debe_cambiar_clave = False
            if usuario.nombre_usuario == "admin":
                config.establecer_contrasena(nueva)
            db.session.add(Auditoria(
                modulo="Configuración", accion="Cambiar contraseña",
                entidad="Usuario", id_entidad=usuario.id_usuario,
                detalle="Contraseña de acceso actualizada.",
            ))
            db.session.commit()
            flash("Contraseña actualizada correctamente.", "success")
            from app.routes.autenticacion import destino_inicial
            return redirect(destino_inicial(usuario))
    return render_template("configuracion/contrasena.html")
