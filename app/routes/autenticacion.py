import re
import time
from urllib.parse import urlsplit

from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, session, url_for,
)

from app.extensions import db
from app.models import Auditoria, Usuario, ahora_utc


bp = Blueprint("autenticacion", __name__, url_prefix="/acceso")


def destino_inicial(usuario):
    if usuario.tiene_permiso("ver_finanzas"):
        return url_for("informacion.general")
    if usuario.tiene_permiso("ver_alumnos"):
        return url_for("alumnos.listar")
    if usuario.tiene_permiso("ver_deportivo"):
        return url_for("calendario.ver")
    return url_for("configuracion.contrasena")


def _destino_local(valor):
    valor = (valor or "").strip()
    partes = urlsplit(valor)
    if valor.startswith("/") and not valor.startswith("//") and not partes.netloc:
        return valor
    return url_for("informacion.general")


@bp.route("/", methods=["GET", "POST"])
def login():
    if session.get("autenticado"):
        return redirect(url_for("informacion.general"))
    destino = _destino_local(request.values.get("next"))
    clave_cliente = request.remote_addr or "local"
    intentos = current_app.extensions.setdefault("intentos_acceso", {})
    estado = intentos.get(clave_cliente, {"fallos": 0, "bloqueado_hasta": 0})
    ahora = time.time()
    if estado["bloqueado_hasta"] > ahora:
        minutos = max(1, int((estado["bloqueado_hasta"] - ahora + 59) // 60))
        flash(f"Acceso bloqueado temporalmente. Intente nuevamente en {minutos} minuto(s).", "danger")
        return render_template("autenticacion/login.html", destino=destino), 429
    if request.method == "POST":
        nombre_usuario = request.form.get("nombre_usuario", "admin").strip().lower()
        contrasena = request.form.get("contrasena", "")
        usuario = Usuario.query.filter(db.func.lower(Usuario.nombre_usuario) == nombre_usuario).first()
        if not re.fullmatch(r"\d{5}", contrasena):
            flash("La contraseña debe contener exactamente 5 números.", "danger")
        elif usuario and usuario.activo and usuario.verificar_contrasena(contrasena):
            intentos.pop(clave_cliente, None)
            session.clear()
            session["autenticado"] = True
            session["id_usuario"] = usuario.id_usuario
            session.permanent = True
            usuario.ultimo_acceso = ahora_utc()
            db.session.add(Auditoria(modulo="Acceso", accion="Iniciar sesión", entidad="Usuario", id_entidad=usuario.id_usuario, id_usuario=usuario.id_usuario))
            db.session.commit()
            if usuario.debe_cambiar_clave:
                flash("Por seguridad, cambie la contraseña inicial desde Configuración.", "warning")
                return redirect(url_for("configuracion.contrasena"))
            if destino == url_for("informacion.general") and not usuario.tiene_permiso("ver_finanzas"):
                destino = destino_inicial(usuario)
            return redirect(destino)
        else:
            estado["fallos"] += 1
            if estado["fallos"] >= 5:
                estado = {"fallos": 0, "bloqueado_hasta": ahora + 300}
                flash("Demasiados intentos incorrectos. Acceso bloqueado durante 5 minutos.", "danger")
            else:
                restantes = 5 - estado["fallos"]
                flash(f"Contraseña incorrecta. Quedan {restantes} intento(s).", "danger")
            intentos[clave_cliente] = estado
    return render_template("autenticacion/login.html", destino=destino)


@bp.route("/salir", methods=["POST"])
def logout():
    if session.get("id_usuario"):
        db.session.add(Auditoria(modulo="Acceso", accion="Cerrar sesión", entidad="Usuario", id_entidad=session["id_usuario"], id_usuario=session["id_usuario"]))
        db.session.commit()
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("autenticacion.login"))
