from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Equipo, Categoria, Partido, Posicion, Auditoria
from app.utils.validacion import ErrorValidacion, entero, texto_requerido

bp = Blueprint("equipos", __name__, url_prefix="/equipos")


@bp.route("/")
def listar():
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    if request.headers.get("HX-Request"):
        return render_template("equipos/_tabla.html", equipos=equipos)
    return render_template("equipos/listar.html", equipos=equipos)


@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    if request.method == "POST":
        try:
            nombre = texto_requerido(request.form.get("nombre"), "Nombre", 120)
            id_categoria = entero(request.form.get("id_categoria"), "Categoría", 1)
            if id_categoria and db.session.get(Categoria, id_categoria) is None:
                raise ErrorValidacion("La categoría seleccionada no existe.")
            existente = Equipo.query.filter(
                db.func.lower(Equipo.nombre) == nombre.lower(),
                Equipo.id_categoria == id_categoria,
                Equipo.es_rival.is_(False),
            ).first()
            if existente:
                raise ErrorValidacion("Ya existe ese equipo en la categoría seleccionada.")
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template("equipos/form.html", equipo=None, categorias=categorias)
        equipo = Equipo(
            nombre=nombre, id_categoria=id_categoria, es_rival=False,
            activo=request.form.get("activo", "1") == "1",
        )
        db.session.add(equipo)
        db.session.flush()
        db.session.add(Auditoria(
            modulo="Equipos", accion="Crear", entidad="Equipo",
            id_entidad=equipo.id_equipo, detalle=equipo.nombre,
        ))
        db.session.commit()
        flash(f"Equipo '{equipo.nombre}' creado.", "success")
        return redirect(url_for("equipos.listar"))
    return render_template("equipos/form.html", equipo=None, categorias=categorias)


@bp.route("/<int:id_equipo>/editar", methods=["GET", "POST"])
def editar(id_equipo):
    equipo = Equipo.query.get_or_404(id_equipo)
    if equipo.es_rival:
        flash("Los rivales se administran desde Campeonatos.", "warning")
        return redirect(url_for("campeonatos.rivales"))
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    if request.method == "POST":
        categoria_anterior = equipo.id_categoria
        nombre_anterior = equipo.nombre
        try:
            nombre = texto_requerido(request.form.get("nombre"), "Nombre", 120)
            id_categoria = entero(request.form.get("id_categoria"), "Categoría", 1)
            if id_categoria and db.session.get(Categoria, id_categoria) is None:
                raise ErrorValidacion("La categoría seleccionada no existe.")
            existente = Equipo.query.filter(
                db.func.lower(Equipo.nombre) == nombre.lower(),
                Equipo.id_categoria == id_categoria,
                Equipo.es_rival.is_(False),
                Equipo.id_equipo != equipo.id_equipo,
            ).first()
            if existente:
                raise ErrorValidacion("Ya existe ese equipo en la categoría seleccionada.")
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template("equipos/form.html", equipo=equipo, categorias=categorias)
        if categoria_anterior != id_categoria and Partido.query.filter(
            db.or_(Partido.id_equipo == id_equipo, Partido.id_equipo_rival == id_equipo),
            Partido.id_campeonato.isnot(None),
        ).first():
            flash("No se puede cambiar la categoría: el equipo ya tiene fixture.", "danger")
            return render_template("equipos/form.html", equipo=equipo, categorias=categorias)
        equipo.nombre, equipo.id_categoria = nombre, id_categoria
        equipo.activo = request.form.get("activo") == "1"
        db.session.add(Auditoria(
            modulo="Equipos", accion="Editar", entidad="Equipo",
            id_entidad=id_equipo,
            detalle=f"{nombre_anterior}/{categoria_anterior} -> {nombre}/{id_categoria}",
        ))
        db.session.commit()
        flash("Equipo actualizado.", "success")
        return redirect(url_for("equipos.listar"))
    return render_template("equipos/form.html", equipo=equipo, categorias=categorias)


@bp.route("/<int:id_equipo>/eliminar", methods=["POST"])
def eliminar(id_equipo):
    equipo = Equipo.query.get_or_404(id_equipo)
    if equipo.es_rival:
        flash("Los rivales se administran desde Campeonatos.", "warning")
        return redirect(url_for("campeonatos.rivales"))
    en_uso = (
        bool(equipo.alumnos or equipo.campeonatos)
        or Partido.query.filter(
            db.or_(
                Partido.id_equipo == id_equipo,
                Partido.id_equipo_rival == id_equipo,
            )
        ).first() is not None
        or Posicion.query.filter_by(id_equipo=id_equipo).first() is not None
    )
    if en_uso:
        flash("No se puede eliminar: hay alumnos asociados a este equipo.", "danger")
        return redirect(url_for("equipos.listar"))
    db.session.add(Auditoria(
        modulo="Equipos", accion="Eliminar", entidad="Equipo",
        id_entidad=id_equipo, detalle=equipo.nombre,
    ))
    db.session.delete(equipo)
    db.session.commit()
    flash("Equipo eliminado.", "success")
    return redirect(url_for("equipos.listar"))
