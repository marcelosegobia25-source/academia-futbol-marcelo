import re
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Auditoria, Permiso, Rol, Usuario

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

@bp.route("/")
def listar():
    return render_template("usuarios/listar.html", usuarios=Usuario.query.order_by(Usuario.nombre_usuario).all(), roles=Rol.query.order_by(Rol.nombre).all(), permisos=Permiso.query.order_by(Permiso.nombre).all())

@bp.route("/roles/<int:id_rol>/permisos", methods=["POST"])
def permisos_rol(id_rol):
    rol = Rol.query.get_or_404(id_rol)
    anterior = ",".join(sorted(p.codigo for p in rol.permisos))
    if rol.nombre == "Administrador":
        rol.permisos = Permiso.query.all()
    else:
        ids = {int(x) for x in request.form.getlist("id_permiso") if x.isdigit()}
        rol.permisos = Permiso.query.filter(Permiso.id_permiso.in_(ids)).all() if ids else []
    nuevo = ",".join(sorted(p.codigo for p in rol.permisos))
    db.session.add(Auditoria(modulo="Usuarios", accion="Cambiar permisos", entidad="Rol", id_entidad=rol.id_rol, valor_anterior=anterior, valor_nuevo=nuevo))
    db.session.commit(); flash("Permisos del rol actualizados.", "success")
    return redirect(url_for("usuarios.listar"))

@bp.route("/nuevo", methods=["POST"])
def nuevo():
    nombre = request.form.get("nombre_usuario", "").strip().lower()
    completo = request.form.get("nombre_completo", "").strip()
    rol = db.session.get(Rol, request.form.get("id_rol", type=int))
    if not re.fullmatch(r"[a-z0-9_.-]{3,40}", nombre) or not completo or not rol:
        flash("Revise el usuario, nombre y rol.", "danger")
    else:
        try:
            usuario = Usuario(nombre_usuario=nombre, nombre_completo=completo, contrasena_hash="", rol=rol)
            usuario.establecer_contrasena("00000")
            db.session.add(usuario); db.session.flush()
            db.session.add(Auditoria(modulo="Usuarios", accion="Crear", entidad="Usuario", id_entidad=usuario.id_usuario, valor_nuevo=f"{nombre}; rol={rol.nombre}"))
            db.session.commit(); flash("Usuario creado con clave temporal 00000.", "success")
        except IntegrityError:
            db.session.rollback(); flash("Ese nombre de usuario ya existe.", "warning")
    return redirect(url_for("usuarios.listar"))

@bp.route("/<int:id_usuario>/actualizar", methods=["POST"])
def actualizar(id_usuario):
    usuario = Usuario.query.get_or_404(id_usuario)
    rol = db.session.get(Rol, request.form.get("id_rol", type=int))
    activo_nuevo = request.form.get("activo") == "1"
    if usuario.id_usuario == g.usuario_actual.id_usuario and (not activo_nuevo or (rol and rol.nombre != "Administrador")):
        flash("No puede desactivar su propia cuenta ni quitarse el rol Administrador.", "danger")
    elif not rol:
        flash("El rol no es válido.", "danger")
    else:
        anterior = f"rol={usuario.rol.nombre}; activo={usuario.activo}"
        usuario.rol = rol; usuario.activo = activo_nuevo
        db.session.add(Auditoria(modulo="Usuarios", accion="Actualizar", entidad="Usuario", id_entidad=usuario.id_usuario, valor_anterior=anterior, valor_nuevo=f"rol={rol.nombre}; activo={usuario.activo}"))
        db.session.commit(); flash("Usuario actualizado.", "success")
    return redirect(url_for("usuarios.listar"))

@bp.route("/<int:id_usuario>/restablecer", methods=["POST"])
def restablecer(id_usuario):
    usuario = Usuario.query.get_or_404(id_usuario)
    usuario.establecer_contrasena("00000"); usuario.debe_cambiar_clave = True
    db.session.add(Auditoria(modulo="Usuarios", accion="Restablecer contraseña", entidad="Usuario", id_entidad=usuario.id_usuario, valor_nuevo="Clave temporal asignada"))
    db.session.commit(); flash("Contraseña restablecida a 00000.", "success")
    return redirect(url_for("usuarios.listar"))
