from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from sqlalchemy.orm import selectinload

from app.models import Alumno, Categoria, Equipo, Partido, Posicion, Auditoria
from app.utils.validacion import ErrorValidacion, entero, texto_requerido
from app.utils.resumen_categorias import construir_resumen_categorias

bp = Blueprint("categorias", __name__, url_prefix="/categorias")


def _validar_solapamiento(edad_min, edad_max, excluir=None):
    if edad_min is None or edad_max is None:
        return
    consulta = Categoria.query.filter(
        Categoria.edad_min.isnot(None), Categoria.edad_max.isnot(None),
        Categoria.edad_min <= edad_max, Categoria.edad_max >= edad_min,
    )
    if excluir:
        consulta = consulta.filter(Categoria.id_categoria != excluir)
    conflicto = consulta.first()
    if conflicto:
        raise ErrorValidacion(
            f"El rango se solapa con {conflicto.nombre_mostrado} "
            f"({conflicto.edad_min}–{conflicto.edad_max} años)."
        )


@bp.route("/")
def listar():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = (
        Equipo.query
        .filter_by(es_rival=False)
        .options(selectinload(Equipo.alumnos))
        .order_by(Equipo.nombre)
        .all()
    )
    alumnos = Alumno.query.order_by(Alumno.apellido, Alumno.nombre).all()
    resumen_categorias = construir_resumen_categorias(
        categorias, equipos, alumnos
    )
    if request.headers.get("HX-Request"):
        return render_template(
            "categorias/_tabla.html",
            resumen_categorias=resumen_categorias,
        )
    return render_template(
        "categorias/listar.html",
        categorias=categorias,
        resumen_categorias=resumen_categorias,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    if request.method == "POST":
        try:
            nombre = texto_requerido(request.form.get("nombre"), "Nombre", 80)
            edad_min = entero(request.form.get("edad_min"), "Edad mínima", 0, 100)
            edad_max = entero(request.form.get("edad_max"), "Edad máxima", 0, 100)
            if (edad_min is None) != (edad_max is None):
                raise ErrorValidacion("Debe indicar ambas edades o dejar ambas vacías.")
            if edad_min is not None and edad_min > edad_max:
                raise ErrorValidacion("La edad mínima no puede superar la edad máxima.")
            _validar_solapamiento(edad_min, edad_max)
            if Categoria.query.filter(db.func.lower(Categoria.nombre) == nombre.lower()).first():
                raise ErrorValidacion("Ya existe una categoría con ese nombre.")
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template("categorias/form.html", categoria=None)
        cat = Categoria(nombre=nombre, edad_min=edad_min, edad_max=edad_max)
        db.session.add(cat)
        db.session.flush()
        db.session.add(Auditoria(
            modulo="Categorías", accion="Crear", entidad="Categoria",
            id_entidad=cat.id_categoria, detalle=f"{cat.nombre}: {edad_min}-{edad_max}",
        ))
        db.session.commit()
        flash(f"Categoría '{cat.nombre}' creada.", "success")
        return redirect(url_for("categorias.listar"))
    return render_template("categorias/form.html", categoria=None)


@bp.route("/<int:id_categoria>/editar", methods=["GET", "POST"])
def editar(id_categoria):
    categoria = Categoria.query.get_or_404(id_categoria)
    if request.method == "POST":
        anterior = f"{categoria.nombre}: {categoria.edad_min}-{categoria.edad_max}"
        try:
            nombre = texto_requerido(request.form.get("nombre"), "Nombre", 80)
            edad_min = entero(request.form.get("edad_min"), "Edad mínima", 0, 100)
            edad_max = entero(request.form.get("edad_max"), "Edad máxima", 0, 100)
            if (edad_min is None) != (edad_max is None):
                raise ErrorValidacion("Debe indicar ambas edades o dejar ambas vacías.")
            if edad_min is not None and edad_min > edad_max:
                raise ErrorValidacion("La edad mínima no puede superar la edad máxima.")
            _validar_solapamiento(edad_min, edad_max, categoria.id_categoria)
            repetida = Categoria.query.filter(
                db.func.lower(Categoria.nombre) == nombre.lower(),
                Categoria.id_categoria != categoria.id_categoria,
            ).first()
            if repetida:
                raise ErrorValidacion("Ya existe una categoría con ese nombre.")
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template("categorias/form.html", categoria=categoria)
        categoria.nombre, categoria.edad_min, categoria.edad_max = nombre, edad_min, edad_max
        afectados = Alumno.query.filter_by(id_categoria=id_categoria).count()
        db.session.add(Auditoria(
            modulo="Categorías", accion="Editar", entidad="Categoria",
            id_entidad=id_categoria,
            detalle=f"{anterior} -> {nombre}: {edad_min}-{edad_max}; alumnos={afectados}",
        ))
        db.session.commit()
        flash("Categoría actualizada.", "success")
        return redirect(url_for("categorias.listar"))
    return render_template("categorias/form.html", categoria=categoria)


@bp.route("/<int:id_categoria>/eliminar", methods=["POST"])
def eliminar(id_categoria):
    categoria = Categoria.query.get_or_404(id_categoria)
    en_uso = (
        bool(categoria.alumnos or categoria.campeonatos or categoria.equipos)
        or Partido.query.filter_by(id_categoria=id_categoria).first() is not None
        or Posicion.query.filter_by(id_categoria=id_categoria).first() is not None
    )
    if en_uso:
        flash("No se puede eliminar: hay alumnos o campeonatos asociados a esta categoría.", "danger")
        return redirect(url_for("categorias.listar"))
    db.session.add(Auditoria(
        modulo="Categorías", accion="Eliminar", entidad="Categoria",
        id_entidad=id_categoria, detalle=categoria.nombre,
    ))
    db.session.delete(categoria)
    db.session.commit()
    flash("Categoría eliminada.", "success")
    return redirect(url_for("categorias.listar"))
