from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g

from app.extensions import db
from app.models import ConflictoAutorizado, EventoAgenda, Categoria, Equipo, Lugar, Auditoria
from app.utils.conflictos_deportivos import detectar_conflictos
from app.utils.validacion import (
    ErrorValidacion, fecha_iso, hora_hm, texto_opcional, texto_requerido,
)

bp = Blueprint("agenda", __name__, url_prefix="/agenda")


@bp.route("/")
def listar():
    consulta = EventoAgenda.query
    if request.args.get("fecha"):
        try:
            consulta = consulta.filter(
                EventoAgenda.fecha == fecha_iso(request.args.get("fecha"), "Fecha")
            )
        except ErrorValidacion:
            flash("La fecha del filtro no es válida.", "warning")
    if request.args.get("id_categoria", type=int):
        consulta = consulta.filter_by(id_categoria=request.args.get("id_categoria", type=int))
    if request.args.get("id_equipo", type=int):
        consulta = consulta.filter_by(id_equipo=request.args.get("id_equipo", type=int))
    if request.args.get("tipo"):
        consulta = consulta.filter_by(tipo=request.args.get("tipo"))
    paginacion = consulta.order_by(
        EventoAgenda.fecha.desc(), EventoAgenda.hora
    ).paginate(page=max(request.args.get("page", 1, type=int), 1), per_page=40, error_out=False)
    eventos = paginacion.items
    contexto = dict(
        eventos=eventos, paginacion=paginacion, filtros=request.args,
        categorias=Categoria.query.order_by(Categoria.nombre).all(),
        equipos=Equipo.query.filter_by(es_rival=False, activo=True).order_by(Equipo.nombre).all(),
    )
    if request.headers.get("HX-Request"):
        return render_template("agenda/_tabla.html", **contexto)
    return render_template("agenda/listar.html", **contexto)


def _relaciones_validas(id_categoria, id_equipo):
    if id_categoria and db.session.get(Categoria, id_categoria) is None:
        raise ErrorValidacion("La categoría seleccionada no existe.")
    equipo = db.session.get(Equipo, id_equipo) if id_equipo else None
    if id_equipo and (equipo is None or equipo.es_rival or not equipo.activo):
        raise ErrorValidacion("El equipo seleccionado no existe o está inactivo.")
    if equipo and equipo.id_categoria and id_categoria and equipo.id_categoria != id_categoria:
        raise ErrorValidacion("El equipo no pertenece a la categoría seleccionada.")


def _lugar_por_nombre(nombre):
    if not nombre:
        return None
    return Lugar.query.filter(db.func.lower(Lugar.nombre) == nombre.lower()).first()


def _conflictos_evento(evento, excluir=None):
    conflictos = detectar_conflictos(
        evento.fecha, evento.hora, evento.id_lugar, evento.lugar,
        evento.id_equipo, excluir_evento=excluir, duracion_minutos=60,
    )
    if not conflictos:
        return []
    usuario = getattr(g, "usuario_actual", None)
    motivo = request.form.get("motivo_conflicto", "").strip()
    if not (request.form.get("autorizar_conflicto") == "1" and motivo and usuario and usuario.tiene_permiso("administrar")):
        raise ErrorValidacion("Conflicto de horario: " + "; ".join(f"{t}: {r}" for t, r in conflictos))
    return conflictos


def _registrar_conflictos_evento(evento, conflictos):
    for tipo, referencia in conflictos:
        db.session.add(ConflictoAutorizado(
            tipo_entidad="EventoAgenda", id_entidad=evento.id_evento,
            tipo_conflicto=tipo, referencia=referencia,
            motivo=request.form.get("motivo_conflicto", "").strip(),
            id_usuario=g.usuario_actual.id_usuario,
        ))


@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()

    if request.method == "POST":
        try:
            id_categoria = request.form.get("id_categoria", type=int) or None
            id_equipo = request.form.get("id_equipo", type=int) or None
            _relaciones_validas(id_categoria, id_equipo)
            nombre_lugar = texto_opcional(request.form.get("lugar"), "Lugar", 150)
            lugar_catalogo = _lugar_por_nombre(nombre_lugar)
            evento = EventoAgenda(
            fecha=fecha_iso(request.form.get("fecha"), "Fecha"),
            hora=hora_hm(request.form.get("hora"), "Hora"),
            descripcion=texto_requerido(request.form.get("descripcion"), "Descripción", 255),
            lugar=nombre_lugar, id_lugar=lugar_catalogo.id_lugar if lugar_catalogo else None,
            id_categoria=id_categoria, id_equipo=id_equipo,
            tipo="Evento",
            )
            conflictos = _conflictos_evento(evento)
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "agenda/form.html", evento=None, categorias=categorias,
                equipos=equipos, lugares=lugares,
            )
        db.session.add(evento)
        db.session.flush()
        _registrar_conflictos_evento(evento, conflictos)
        db.session.add(Auditoria(
            modulo="Agenda", accion="Crear", entidad="EventoAgenda",
            id_entidad=evento.id_evento, detalle=evento.descripcion,
        ))
        db.session.commit()
        flash("Evento agregado a la agenda.", "success")
        return redirect(url_for("agenda.listar"))

    return render_template(
        "agenda/form.html", evento=None, categorias=categorias,
        equipos=equipos, lugares=lugares,
    )


@bp.route("/<int:id_evento>/editar", methods=["GET", "POST"])
def editar(id_evento):
    evento = EventoAgenda.query.get_or_404(id_evento)
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()

    if evento.tipo == "Partido":
        flash("Este evento proviene de un partido programado. Edítelo desde el módulo Partidos.", "warning")
        return redirect(url_for("agenda.listar"))

    if request.method == "POST":
        try:
            id_categoria = request.form.get("id_categoria", type=int) or None
            id_equipo = request.form.get("id_equipo", type=int) or None
            _relaciones_validas(id_categoria, id_equipo)
            evento.fecha = fecha_iso(request.form.get("fecha"), "Fecha")
            evento.hora = hora_hm(request.form.get("hora"), "Hora")
            evento.descripcion = texto_requerido(
                request.form.get("descripcion"), "Descripción", 255
            )
            evento.lugar = texto_opcional(request.form.get("lugar"), "Lugar", 150)
            lugar_catalogo = _lugar_por_nombre(evento.lugar)
            evento.id_lugar = lugar_catalogo.id_lugar if lugar_catalogo else None
            evento.id_categoria = id_categoria
            evento.id_equipo = id_equipo
            conflictos = _conflictos_evento(evento, evento.id_evento)
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "agenda/form.html", evento=evento, categorias=categorias,
                equipos=equipos, lugares=lugares,
            )
        _registrar_conflictos_evento(evento, conflictos)
        db.session.add(Auditoria(
            modulo="Agenda", accion="Editar", entidad="EventoAgenda",
            id_entidad=evento.id_evento, detalle=evento.descripcion,
        ))
        db.session.commit()
        flash("Evento actualizado.", "success")
        return redirect(url_for("agenda.listar"))

    return render_template(
        "agenda/form.html", evento=evento, categorias=categorias,
        equipos=equipos, lugares=lugares,
    )


@bp.route("/<int:id_evento>/eliminar", methods=["POST"])
def eliminar(id_evento):
    evento = EventoAgenda.query.get_or_404(id_evento)
    if evento.fecha < date.today():
        flash("Los eventos históricos no se eliminan; deben conservarse para auditoría.", "danger")
        return redirect(url_for("agenda.listar"))
    if evento.tipo == "Partido":
        flash("Este evento proviene de un partido. Elimínelo desde el módulo Partidos.", "warning")
        return redirect(url_for("agenda.listar"))
    db.session.add(Auditoria(
        modulo="Agenda", accion="Eliminar", entidad="EventoAgenda",
        id_entidad=evento.id_evento, detalle=evento.descripcion,
    ))
    db.session.delete(evento)
    db.session.commit()
    flash("Evento eliminado.", "success")
    return redirect(url_for("agenda.listar"))
