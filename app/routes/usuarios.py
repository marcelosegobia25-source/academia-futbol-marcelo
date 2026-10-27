import re
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Auditoria, Permiso, Rol, Usuario
from app.utils.autorizacion import CATEGORIAS_PERMISOS

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@bp.route("/")
def listar():
    return render_template(
        "usuarios/listar.html",
        usuarios=Usuario.query.order_by(Usuario.nombre_usuario).all(),
        roles=Rol.query.order_by(Rol.nombre).all(),
        categorias_permisos=CATEGORIAS_PERMISOS,
        permisos=Permiso.query.order_by(Permiso.id_permiso).all(),
    )


@bp.route("/roles/nuevo", methods=["POST"])
def crear_rol():
    nombre = request.form.get("nombre", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    if not nombre:
        flash("El nombre del rol es obligatorio.", "danger")
        return redirect(url_for("usuarios.listar"))

    existente = Rol.query.filter(db.func.lower(Rol.nombre) == nombre.lower()).first()
    if existente:
        flash(f"Ya existe un rol con el nombre '{nombre}'.", "warning")
        return redirect(url_for("usuarios.listar"))

    ids_permisos = {int(x) for x in request.form.getlist("id_permiso") if x.isdigit()}
    permisos_seleccionados = (
        Permiso.query.filter(Permiso.id_permiso.in_(ids_permisos)).all()
        if ids_permisos
        else []
    )

    rol = Rol(nombre=nombre, descripcion=descripcion, permisos=permisos_seleccionados)
    db.session.add(rol)
    db.session.flush()

    id_usuario = g.usuario_actual.id_usuario if getattr(g, "usuario_actual", None) else None
    db.session.add(Auditoria(
        modulo="Usuarios",
        accion="Crear rol",
        entidad="Rol",
        id_entidad=rol.id_rol,
        id_usuario=id_usuario,
        valor_nuevo=f"Rol: {nombre} ({len(permisos_seleccionados)} permisos)",
        detalle=f"Se creó el rol personalizado '{nombre}' con {len(permisos_seleccionados)} permisos asignados.",
    ))
    db.session.commit()
    flash(f"Rol '{nombre}' creado exitosamente con {len(permisos_seleccionados)} permisos asignados.", "success")
    return redirect(url_for("usuarios.listar"))


@bp.route("/roles/<int:id_rol>/editar", methods=["POST"])
def editar_rol(id_rol):
    rol = Rol.query.get_or_404(id_rol)
    nombre = request.form.get("nombre", "").strip()
    descripcion = request.form.get("descripcion", "").strip()

    if rol.nombre == "Administrador":
        flash("El rol Administrador es el rol principal del sistema y no puede ser modificado.", "danger")
        return redirect(url_for("usuarios.listar"))

    if not nombre:
        flash("El nombre del rol no puede quedar vacío.", "danger")
        return redirect(url_for("usuarios.listar"))

    existente = Rol.query.filter(db.func.lower(Rol.nombre) == nombre.lower(), Rol.id_rol != id_rol).first()
    if existente:
        flash(f"Ya existe otro rol con el nombre '{nombre}'.", "warning")
        return redirect(url_for("usuarios.listar"))

    anterior = f"nombre={rol.nombre}; descripcion={rol.descripcion or ''}"
    rol.nombre = nombre
    rol.descripcion = descripcion

    id_usuario = g.usuario_actual.id_usuario if getattr(g, "usuario_actual", None) else None
    db.session.add(Auditoria(
        modulo="Usuarios",
        accion="Editar rol",
        entidad="Rol",
        id_entidad=rol.id_rol,
        id_usuario=id_usuario,
        valor_anterior=anterior,
        valor_nuevo=f"nombre={rol.nombre}; descripcion={rol.descripcion}",
        detalle=f"Se actualizaron los datos del rol #{rol.id_rol} a '{nombre}'.",
    ))
    db.session.commit()
    flash(f"Datos del rol '{nombre}' actualizados correctamente.", "success")
    return redirect(url_for("usuarios.listar"))


@bp.route("/roles/<int:id_rol>/eliminar", methods=["POST"])
def eliminar_rol(id_rol):
    rol = Rol.query.get_or_404(id_rol)
    if rol.nombre == "Administrador":
        flash("El rol Administrador no puede ser eliminado.", "danger")
        return redirect(url_for("usuarios.listar"))

    usuarios_asignados = len(rol.usuarios)
    if usuarios_asignados > 0:
        flash(
            f"No se puede eliminar el rol '{rol.nombre}' porque está asignado a {usuarios_asignados} usuario(s). "
            f"Reasigne primero esos usuarios a otro rol.",
            "danger",
        )
        return redirect(url_for("usuarios.listar"))

    nombre_rol = rol.nombre
    db.session.delete(rol)

    id_usuario = g.usuario_actual.id_usuario if getattr(g, "usuario_actual", None) else None
    db.session.add(Auditoria(
        modulo="Usuarios",
        accion="Eliminar rol",
        entidad="Rol",
        id_entidad=id_rol,
        id_usuario=id_usuario,
        valor_anterior=f"Rol: {nombre_rol}",
        valor_nuevo="Eliminado",
        detalle=f"Se eliminó el rol personalizado '{nombre_rol}'.",
    ))
    db.session.commit()
    flash(f"Rol '{nombre_rol}' eliminado exitosamente.", "success")
    return redirect(url_for("usuarios.listar"))


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

    id_usuario = g.usuario_actual.id_usuario if getattr(g, "usuario_actual", None) else None
    db.session.add(Auditoria(
        modulo="Usuarios",
        accion="Cambiar permisos",
        entidad="Rol",
        id_entidad=rol.id_rol,
        id_usuario=id_usuario,
        valor_anterior=anterior,
        valor_nuevo=nuevo,
        detalle=f"Se actualizaron los permisos del rol '{rol.nombre}' ({len(rol.permisos)} permisos activos).",
    ))
    db.session.commit()
    flash(f"Permisos del rol '{rol.nombre}' actualizados correctamente.", "success")
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
            db.session.add(usuario)
            db.session.flush()

            id_usuario = g.usuario_actual.id_usuario if getattr(g, "usuario_actual", None) else None
            db.session.add(Auditoria(
                modulo="Usuarios",
                accion="Crear",
                entidad="Usuario",
                id_entidad=usuario.id_usuario,
                id_usuario=id_usuario,
                valor_nuevo=f"{nombre}; rol={rol.nombre}",
                detalle=f"Se creó el usuario '{nombre}' ({completo}) con rol '{rol.nombre}'.",
            ))
            db.session.commit()
            flash("Usuario creado con clave temporal 00000.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Ese nombre de usuario ya existe.", "warning")
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
        usuario.rol = rol
        usuario.activo = activo_nuevo

        id_usuario_actor = g.usuario_actual.id_usuario if getattr(g, "usuario_actual", None) else None
        db.session.add(Auditoria(
            modulo="Usuarios",
            accion="Actualizar",
            entidad="Usuario",
            id_entidad=usuario.id_usuario,
            id_usuario=id_usuario_actor,
            valor_anterior=anterior,
            valor_nuevo=f"rol={rol.nombre}; activo={usuario.activo}",
            detalle=f"Se actualizó la cuenta de '{usuario.nombre_usuario}': rol={rol.nombre}, activo={usuario.activo}.",
        ))
        db.session.commit()
        flash("Usuario actualizado.", "success")
    return redirect(url_for("usuarios.listar"))


@bp.route("/<int:id_usuario>/restablecer", methods=["POST"])
def restablecer(id_usuario):
    usuario = Usuario.query.get_or_404(id_usuario)
    usuario.establecer_contrasena("00000")
    usuario.debe_cambiar_clave = True

    id_usuario_actor = g.usuario_actual.id_usuario if getattr(g, "usuario_actual", None) else None
    db.session.add(Auditoria(
        modulo="Usuarios",
        accion="Restablecer contraseña",
        entidad="Usuario",
        id_entidad=usuario.id_usuario,
        id_usuario=id_usuario_actor,
        valor_nuevo="Clave temporal 00000 asignada",
        detalle=f"Se restableció la contraseña de '{usuario.nombre_usuario}' a la clave temporal 00000.",
    ))
    db.session.commit()
    flash("Contraseña restablecida a 00000.", "success")
    return redirect(url_for("usuarios.listar"))
