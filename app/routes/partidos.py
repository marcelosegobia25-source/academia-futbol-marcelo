from datetime import datetime, date
from calendar import monthrange
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, g

from app.extensions import db
from app.models import Partido, Equipo, Categoria, Campeonato, ConflictoAutorizado, EventoAgenda, Lugar, Auditoria
from app.utils.conflictos_deportivos import detectar_conflictos, es_duplicado_partido
from app.utils.pdf_tablas import generar_tabla_pdf
from app.utils.descargas import enviar_buffer
from app.utils.validacion import (
    ErrorValidacion, entero, fecha_iso, hora_hm, texto_opcional, texto_requerido,
)

bp = Blueprint("partidos", __name__, url_prefix="/partidos")


def _validar_programacion(fecha, hora, id_equipo, id_equipo_rival, rival, id_lugar, cancha, excluir=None):
    duplicado = es_duplicado_partido(fecha, hora, id_equipo, id_equipo_rival, rival, excluir)
    if duplicado:
        raise ErrorValidacion(f"Ya existe el partido #{duplicado.id_partido} con los mismos equipos, fecha y hora.")
    conflictos = detectar_conflictos(
        fecha, hora, id_lugar=id_lugar, nombre_lugar=cancha,
        id_equipo=id_equipo, id_equipo_rival=id_equipo_rival,
        excluir_partido=excluir,
    )
    if not conflictos:
        return []
    usuario = getattr(g, "usuario_actual", None)
    motivo = request.form.get("motivo_conflicto", "").strip()
    autorizado = request.form.get("autorizar_conflicto") == "1"
    if not (autorizado and motivo and usuario and usuario.tiene_permiso("administrar")):
        resumen = "; ".join(f"{tipo}: {ref}" for tipo, ref in conflictos)
        raise ErrorValidacion(f"Conflicto de horario: {resumen}. Solo un administrador puede autorizarlo con un motivo.")
    return conflictos


def _guardar_conflictos(partido, conflictos):
    for tipo, referencia in conflictos:
        db.session.add(ConflictoAutorizado(
            tipo_entidad="Partido", id_entidad=partido.id_partido,
            tipo_conflicto=tipo, referencia=referencia,
            motivo=request.form.get("motivo_conflicto", "").strip(),
            id_usuario=g.usuario_actual.id_usuario,
        ))


def _filtrar_partidos(args):
    id_equipo = args.get("id_equipo", type=int)
    id_categoria = args.get("id_categoria", type=int)
    rival = args.get("rival", "").strip()
    cancha = args.get("cancha", "").strip()
    fecha = args.get("fecha", "")
    rango = args.get("rango", "")  # 'mes_actual' | 'mes_siguiente'

    query = Partido.query
    if id_equipo:
        query = query.filter_by(id_equipo=id_equipo)
    if id_categoria:
        query = query.filter_by(id_categoria=id_categoria)
    if rival:
        query = query.filter(Partido.rival.ilike(f"%{rival}%"))
    if cancha:
        query = query.filter(Partido.cancha.ilike(f"%{cancha}%"))
    if fecha:
        query = query.filter(Partido.fecha == datetime.strptime(fecha, "%Y-%m-%d").date())

    if rango in ("mes_actual", "mes_siguiente"):
        hoy = date.today()
        mes = hoy.month if rango == "mes_actual" else (hoy.month % 12) + 1
        anio = hoy.year if rango == "mes_actual" or hoy.month < 12 else hoy.year + 1
        _, ultimo_dia = monthrange(anio, mes)
        query = query.filter(
            Partido.fecha >= date(anio, mes, 1), Partido.fecha <= date(anio, mes, ultimo_dia)
        )

    return query.order_by(Partido.fecha.asc(), Partido.hora.asc()).all()


@bp.route("/")
def listar():
    partidos = _filtrar_partidos(request.args)
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    categorias = Categoria.query.order_by(Categoria.nombre).all()

    contexto = dict(partidos=partidos, equipos=equipos, categorias=categorias, filtros=request.args)
    if request.headers.get("HX-Request"):
        return render_template("partidos/_tabla.html", **contexto)
    return render_template("partidos/listar.html", **contexto)


@bp.route("/convocatoria.pdf", methods=["POST"])
def convocatoria_pdf():
    ids = request.form.getlist("seleccionados")
    if not ids:
        flash("Seleccione al menos un partido para generar la convocatoria.", "warning")
        return redirect(url_for("partidos.listar"))

    partidos = Partido.query.filter(Partido.id_partido.in_(ids)).order_by(Partido.fecha, Partido.hora).all()
    encabezados = [
        "Fecha", "Hora", "Categoría", "Equipo local", "Rival",
        "Lugar", "Google Maps",
    ]
    filas = [[
        p.fecha.strftime("%d/%m/%Y"), p.hora.strftime("%H:%M") if p.hora else "-",
        p.categoria.nombre, p.equipo.nombre, p.rival, p.cancha or "-",
        p.lugar_catalogo.google_maps_url if p.lugar_catalogo and p.lugar_catalogo.google_maps_url else "-",
    ] for p in partidos]
    buffer = generar_tabla_pdf("Convocatoria de partidos", encabezados, filas)
    nombre = f"convocatoria_{date.today().isoformat()}.pdf"
    return enviar_buffer(buffer, "partidos", nombre, "application/pdf")


@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    campeonatos = Campeonato.query.order_by(Campeonato.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()

    if request.method == "POST":
        try:
            fecha_partido = fecha_iso(request.form.get("fecha"), "Fecha")
            hora_partido = hora_hm(request.form.get("hora"), "Hora")
            rival = texto_requerido(request.form.get("rival"), "Rival", 150)
            cancha = texto_opcional(request.form.get("cancha"), "Cancha", 150)
            lugar_catalogo = Lugar.query.filter(
                db.func.lower(Lugar.nombre) == cancha.lower()
            ).first() if cancha else None
            id_equipo = entero(
                request.form.get("id_equipo"), "Equipo", 1, requerido=True
            )
            id_categoria = entero(
                request.form.get("id_categoria"), "Categoría", 1, requerido=True
            )
            id_campeonato = entero(request.form.get("id_campeonato"), "Campeonato", 1)
            equipo_local = db.session.get(Equipo, id_equipo)
            if equipo_local is None or equipo_local.es_rival:
                raise ErrorValidacion("El equipo seleccionado no existe.")
            if db.session.get(Categoria, id_categoria) is None:
                raise ErrorValidacion("La categoría seleccionada no existe.")
            if id_campeonato and db.session.get(Campeonato, id_campeonato) is None:
                raise ErrorValidacion("El campeonato seleccionado no existe.")
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "partidos/form.html", partido=None, equipos=equipos,
                categorias=categorias, campeonatos=campeonatos, lugares=lugares,
            )
        equipo_rival = Equipo.query.filter(
            db.func.lower(Equipo.nombre) == rival.lower(),
            db.or_(Equipo.id_categoria.is_(None), Equipo.id_categoria == id_categoria),
        ).first()
        if equipo_rival and equipo_rival.id_equipo == id_equipo:
            flash("El equipo local y el rival no pueden ser el mismo.", "danger")
            return render_template(
                "partidos/form.html", partido=None, equipos=equipos,
                categorias=categorias, campeonatos=campeonatos, lugares=lugares,
            )
        try:
            conflictos = _validar_programacion(
                fecha_partido, hora_partido, id_equipo,
                equipo_rival.id_equipo if equipo_rival else None, rival,
                lugar_catalogo.id_lugar if lugar_catalogo else None, cancha,
            )
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template("partidos/form.html", partido=None, equipos=equipos, categorias=categorias, campeonatos=campeonatos, lugares=lugares)
        partido = Partido(
            fecha=fecha_partido,
            hora=hora_partido,
            cancha=cancha,
            id_lugar=lugar_catalogo.id_lugar if lugar_catalogo else None,
            resultado=request.form.get("resultado") or None,
            id_equipo=id_equipo,
            id_categoria=id_categoria,
            rival=rival,
            id_equipo_rival=equipo_rival.id_equipo if equipo_rival else None,
            id_campeonato=id_campeonato,
        )
        db.session.add(partido)
        db.session.flush()
        _guardar_conflictos(partido, conflictos)

        # Se agrega automáticamente a la agenda, como indica el requerimiento.
        evento = EventoAgenda(
            hora=partido.hora,
            fecha=partido.fecha,
            descripcion=f"Partido vs {partido.rival}",
            lugar=partido.cancha,
            id_lugar=partido.id_lugar,
            id_categoria=partido.id_categoria,
            id_equipo=partido.id_equipo,
            tipo="Partido",
            id_partido=partido.id_partido,
        )
        db.session.add(evento)
        db.session.add(Auditoria(
            modulo="Partidos", accion="Crear", entidad="Partido",
            id_entidad=partido.id_partido,
            detalle=f"{partido.fecha} {partido.equipo.nombre} vs {partido.rival}",
        ))
        db.session.commit()

        flash("Partido programado y agregado a la agenda.", "success")
        return redirect(url_for("partidos.listar"))

    return render_template(
        "partidos/form.html", partido=None, equipos=equipos,
        categorias=categorias, campeonatos=campeonatos, lugares=lugares,
    )


@bp.route("/<int:id_partido>/editar", methods=["GET", "POST"])
def editar(id_partido):
    partido = Partido.query.get_or_404(id_partido)
    if partido.id_campeonato is not None:
        flash(
            "Los partidos de campeonato solo pueden editarse desde su fixture.",
            "warning",
        )
        return redirect(url_for(
            "campeonatos.editar_partido_manual",
            id_campeonato=partido.id_campeonato, id_partido=partido.id_partido,
        ))
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    campeonatos = Campeonato.query.order_by(Campeonato.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()

    if request.method == "POST":
        try:
            partido.fecha = fecha_iso(request.form.get("fecha"), "Fecha")
            partido.hora = hora_hm(request.form.get("hora"), "Hora")
            partido.cancha = texto_opcional(request.form.get("cancha"), "Cancha", 150)
            lugar_catalogo = Lugar.query.filter(
                db.func.lower(Lugar.nombre) == partido.cancha.lower()
            ).first() if partido.cancha else None
            partido.id_lugar = lugar_catalogo.id_lugar if lugar_catalogo else None
            partido.id_equipo = entero(
                request.form.get("id_equipo"), "Equipo", 1, requerido=True
            )
            partido.id_categoria = entero(
                request.form.get("id_categoria"), "Categoría", 1, requerido=True
            )
            partido.rival = texto_requerido(request.form.get("rival"), "Rival", 150)
            partido.id_campeonato = entero(
                request.form.get("id_campeonato"), "Campeonato", 1
            )
            equipo_local = db.session.get(Equipo, partido.id_equipo)
            if equipo_local is None or equipo_local.es_rival:
                raise ErrorValidacion("El equipo seleccionado no existe.")
            if db.session.get(Categoria, partido.id_categoria) is None:
                raise ErrorValidacion("La categoría seleccionada no existe.")
            if partido.id_campeonato and db.session.get(
                Campeonato, partido.id_campeonato
            ) is None:
                raise ErrorValidacion("El campeonato seleccionado no existe.")
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "partidos/form.html", partido=partido, equipos=equipos,
                categorias=categorias, campeonatos=campeonatos, lugares=lugares,
            )
        if partido.id_campeonato is None:
            partido.resultado = request.form.get("resultado") or None
        equipo_rival = Equipo.query.filter(
            db.func.lower(Equipo.nombre) == partido.rival.lower(),
            db.or_(
                Equipo.id_categoria.is_(None),
                Equipo.id_categoria == partido.id_categoria,
            ),
        ).first()
        partido.id_equipo_rival = equipo_rival.id_equipo if equipo_rival else None
        try:
            conflictos = _validar_programacion(
                partido.fecha, partido.hora, partido.id_equipo, partido.id_equipo_rival,
                partido.rival, partido.id_lugar, partido.cancha, partido.id_partido,
            )
        except ErrorValidacion as error:
            db.session.rollback(); flash(str(error), "danger")
            return render_template("partidos/form.html", partido=partido, equipos=equipos, categorias=categorias, campeonatos=campeonatos, lugares=lugares)
        _guardar_conflictos(partido, conflictos)
        evento = EventoAgenda.query.filter_by(id_partido=partido.id_partido).first()
        if evento:
            evento.fecha = partido.fecha
            evento.hora = partido.hora
            evento.descripcion = f"Partido vs {partido.rival}"
            evento.lugar = partido.cancha
            evento.id_lugar = partido.id_lugar
            evento.id_categoria = partido.id_categoria
            evento.id_equipo = partido.id_equipo
        db.session.add(Auditoria(
            modulo="Partidos", accion="Editar", entidad="Partido",
            id_entidad=partido.id_partido, detalle=f"{partido.fecha} vs {partido.rival}",
        ))
        db.session.commit()

        flash("Partido actualizado.", "success")
        return redirect(url_for("partidos.listar"))

    return render_template(
        "partidos/form.html", partido=partido, equipos=equipos,
        categorias=categorias, campeonatos=campeonatos, lugares=lugares,
    )


@bp.route("/<int:id_partido>/eliminar", methods=["POST"])
def eliminar(id_partido):
    partido = Partido.query.get_or_404(id_partido)
    if partido.resultado or partido.estado_partido in {"Finalizado", "Walkover", "Cancelado"}:
        flash("Los partidos históricos o finalizados no se eliminan; deben conservarse para auditoría.", "danger")
        return redirect(url_for("partidos.listar"))
    if partido.id_campeonato is not None:
        flash("Elimine el partido únicamente desde el fixture del campeonato.", "danger")
        return redirect(url_for(
            "campeonatos.detalle", id_campeonato=partido.id_campeonato
        ))
    id_campeonato = partido.id_campeonato
    EventoAgenda.query.filter_by(id_partido=partido.id_partido).delete()
    db.session.add(Auditoria(
        modulo="Partidos", accion="Eliminar", entidad="Partido",
        id_entidad=partido.id_partido, detalle=f"{partido.fecha} vs {partido.rival}",
    ))
    db.session.delete(partido)
    db.session.flush()
    if id_campeonato:
        from app.routes.campeonatos import _recalcular_posiciones
        _recalcular_posiciones(id_campeonato)
    db.session.commit()
    flash("Partido eliminado.", "success")
    return redirect(url_for("partidos.listar"))
