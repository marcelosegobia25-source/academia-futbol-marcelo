from datetime import date, datetime, timedelta, time
from flask import Blueprint, render_template, request, redirect, url_for, flash, g

from app.extensions import db
from app.models import ConflictoAutorizado, EventoAgenda, Categoria, Equipo, Lugar, Auditoria, Entrenamiento
from app.utils.conflictos_deportivos import detectar_conflictos
from app.utils.tiempo import hoy_bolivia
from app.utils.validacion import (
    ErrorValidacion, fecha_iso, hora_hm, texto_opcional, texto_requerido,
)

bp = Blueprint("agenda", __name__, url_prefix="/agenda")


@bp.route("/")
def listar():
    filtro_fecha = None
    if request.args.get("fecha"):
        try:
            filtro_fecha = fecha_iso(request.args.get("fecha"), "Fecha")
        except ErrorValidacion:
            flash("La fecha del filtro no es válida.", "warning")
            filtro_fecha = None

    id_categoria = request.args.get("id_categoria", type=int)
    id_equipo = request.args.get("id_equipo", type=int)
    tipo_filtro = (request.args.get("tipo") or "").strip()

    hoy = hoy_bolivia()

    # 1. Consulta de EventoAgenda (Partidos, Eventos y Entrenamientos puntuales)
    consulta = EventoAgenda.query
    if filtro_fecha:
        consulta = consulta.filter(EventoAgenda.fecha == filtro_fecha)
    if id_categoria:
        consulta = consulta.filter_by(id_categoria=id_categoria)
    if id_equipo:
        consulta = consulta.filter_by(id_equipo=id_equipo)
    if tipo_filtro:
        consulta = consulta.filter_by(tipo=tipo_filtro)

    eventos = list(consulta.all())

    # 2. Incorporar entrenamientos semanales fijos si no se filtra por otro tipo
    if not tipo_filtro or tipo_filtro == "Entrenamiento":
        q_entrenamientos = Entrenamiento.query.filter_by(activo=True)
        if id_categoria:
            q_entrenamientos = q_entrenamientos.filter_by(id_categoria=id_categoria)
        if id_equipo:
            q_entrenamientos = q_entrenamientos.filter_by(id_equipo=id_equipo)
        entrenamientos = q_entrenamientos.all()

        if filtro_fecha:
            fechas_evaluar = [filtro_fecha]
        else:
            # Ventana razonable para la agenda general: 7 días pasados hasta 30 días a futuro
            inicio_rango = hoy - timedelta(days=7)
            fin_rango = hoy + timedelta(days=30)
            fechas_evaluar = []
            f_actual = inicio_rango
            while f_actual <= fin_rango:
                fechas_evaluar.append(f_actual)
                f_actual += timedelta(days=1)

        class ItemEntrenamientoAgenda:
            def __init__(self, entrenamiento, fecha):
                self.fecha = fecha
                self.hora = entrenamiento.hora_inicio
                self.hora_fin = entrenamiento.hora_fin
                self.tipo = "Entrenamiento"
                etiqueta = entrenamiento.equipo.nombre if entrenamiento.equipo else (
                    entrenamiento.categoria.nombre if entrenamiento.categoria else "General"
                )
                self.descripcion = f"Entrenamiento - {etiqueta}"
                self.lugar = entrenamiento.lugar
                self.id_lugar = entrenamiento.id_lugar
                self.lugar_catalogo = entrenamiento.lugar_catalogo
                self.id_categoria = entrenamiento.id_categoria
                self.categoria = entrenamiento.categoria
                self.id_equipo = entrenamiento.id_equipo
                self.equipo = entrenamiento.equipo
                self.id_evento = None
                self.id_entrenamiento = entrenamiento.id_entrenamiento
                self.entrenador = entrenamiento.entrenador

        for e in entrenamientos:
            for f in fechas_evaluar:
                if e.fecha_inicio and f < e.fecha_inicio:
                    continue
                if e.fecha_fin and f > e.fecha_fin:
                    continue
                if f.weekday() == e.dia_semana:
                    eventos.append(ItemEntrenamientoAgenda(e, f))

    # Ordenar cronológicamente
    if filtro_fecha:
        eventos.sort(key=lambda x: (x.hora is None, x.hora or time.max, x.descripcion))
    else:
        # Orden descendente por fecha, y ascendente por hora dentro de la misma fecha
        eventos.sort(key=lambda x: (x.fecha, -(x.hora.hour * 60 + x.hora.minute if x.hora else 0)), reverse=True)

    # Paginación manual de la lista combinada
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 40
    total = len(eventos)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    items_pagina = eventos[(page - 1) * per_page : page * per_page]

    class PaginadorCustom:
        def __init__(self, p, per_p, tot, pags):
            self.page = p
            self.per_page = per_p
            self.total = tot
            self.pages = pags
        def iter_pages(self):
            for i in range(1, self.pages + 1):
                yield i

    paginacion = PaginadorCustom(page, per_page, total, total_pages)

    contexto = dict(
        eventos=items_pagina, paginacion=paginacion, filtros=request.args,
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
    equipos = Equipo.query.filter_by(es_rival=False, activo=True).order_by(Equipo.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()

    if request.method == "POST":
        try:
            id_categoria = request.form.get("id_categoria", type=int) or None
            id_equipo = request.form.get("id_equipo", type=int) or None
            _relaciones_validas(id_categoria, id_equipo)
            nombre_lugar = texto_opcional(request.form.get("lugar"), "Lugar", 150)
            lugar_catalogo = _lugar_por_nombre(nombre_lugar)
            tipo = request.form.get("tipo", "Evento").strip()
            if tipo not in ("Evento", "Entrenamiento"):
                tipo = "Evento"

            evento = EventoAgenda(
                fecha=fecha_iso(request.form.get("fecha"), "Fecha"),
                hora=hora_hm(request.form.get("hora"), "Hora"),
                descripcion=texto_requerido(request.form.get("descripcion"), "Descripción", 255),
                lugar=nombre_lugar, id_lugar=lugar_catalogo.id_lugar if lugar_catalogo else None,
                id_categoria=id_categoria, id_equipo=id_equipo,
                tipo=tipo,
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
        usuario_id = getattr(getattr(g, "usuario_actual", None), "id_usuario", None)
        db.session.add(Auditoria(
            modulo="Agenda", accion="Crear", entidad="EventoAgenda",
            id_entidad=evento.id_evento, detalle=f"[{evento.tipo}] {evento.descripcion} ({evento.fecha} {evento.hora or ''})",
            id_usuario=usuario_id,
        ))
        db.session.commit()
        flash(f"{evento.tipo} agregado a la agenda.", "success")
        return redirect(url_for("agenda.listar"))

    return render_template(
        "agenda/form.html", evento=None, categorias=categorias,
        equipos=equipos, lugares=lugares,
    )


@bp.route("/<int:id_evento>/editar", methods=["GET", "POST"])
def editar(id_evento):
    evento = EventoAgenda.query.get_or_404(id_evento)
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = Equipo.query.filter_by(es_rival=False, activo=True).order_by(Equipo.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()

    if evento.tipo == "Partido":
        flash("Este evento proviene de un partido programado. Edítelo desde el módulo Partidos.", "warning")
        return redirect(url_for("agenda.listar"))

    if request.method == "POST":
        try:
            id_categoria = request.form.get("id_categoria", type=int) or None
            id_equipo = request.form.get("id_equipo", type=int) or None
            _relaciones_validas(id_categoria, id_equipo)
            tipo = request.form.get("tipo", evento.tipo).strip()
            if tipo in ("Evento", "Entrenamiento"):
                evento.tipo = tipo
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
        usuario_id = getattr(getattr(g, "usuario_actual", None), "id_usuario", None)
        db.session.add(Auditoria(
            modulo="Agenda", accion="Editar", entidad="EventoAgenda",
            id_entidad=evento.id_evento, detalle=f"[{evento.tipo}] {evento.descripcion} ({evento.fecha} {evento.hora or ''})",
            id_usuario=usuario_id,
        ))
        db.session.commit()
        flash("Actividad actualizada en la agenda.", "success")
        return redirect(url_for("agenda.listar"))

    return render_template(
        "agenda/form.html", evento=evento, categorias=categorias,
        equipos=equipos, lugares=lugares,
    )


@bp.route("/<int:id_evento>/eliminar", methods=["POST"])
def eliminar(id_evento):
    evento = EventoAgenda.query.get_or_404(id_evento)
    if evento.fecha < hoy_bolivia():
        flash("Los eventos históricos no se eliminan; deben conservarse para auditoría.", "danger")
        return redirect(url_for("agenda.listar"))
    if evento.tipo == "Partido":
        flash("Este evento proviene de un partido. Elimínelo desde el módulo Partidos.", "warning")
        return redirect(url_for("agenda.listar"))
    usuario_id = getattr(getattr(g, "usuario_actual", None), "id_usuario", None)
    db.session.add(Auditoria(
        modulo="Agenda", accion="Eliminar", entidad="EventoAgenda",
        id_entidad=evento.id_evento, detalle=f"[{evento.tipo}] {evento.descripcion}",
        id_usuario=usuario_id,
    ))
    db.session.delete(evento)
    db.session.commit()
    flash("Evento eliminado de la agenda.", "success")
    return redirect(url_for("agenda.listar"))
