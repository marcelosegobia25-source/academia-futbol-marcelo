import os
from datetime import date, datetime, timedelta, timezone
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, Response,
    send_file, current_app, g,
)

from app.extensions import db
from app.models import (
    Campeonato, Categoria, Equipo, Partido, Posicion, Alumno, AlumnoCampeonato,
    ConflictoAutorizado, EventoAgenda, Lugar, CampeonatoCategoriaConfig, PodioCampeonato, Auditoria,
)
from app.utils.conflictos_deportivos import detectar_conflictos, es_duplicado_partido
from app.utils.pdf_tablas import generar_tabla_pdf
from app.utils.excel import exportar_tabla_excel
from app.utils.descargas import enviar_buffer, guardar_texto
from app.utils.validacion import (
    ErrorValidacion, entero, fecha_iso, opcion, rango_fechas,
    texto_opcional, texto_requerido,
)
from app.utils.personalizacion import configuracion_y_logo
from sqlalchemy import case

bp = Blueprint("campeonatos", __name__, url_prefix="/campeonatos")

ESTADOS_CAMPEONATO = ["Borrador", "Planificado", "En curso", "Finalizado", "Cancelado"]
FORMATOS_CAMPEONATO = ["Liga", "Eliminación directa", "Liga + eliminatorias", "Manual"]
FASES = ["Liga", "Grupos", "Cuartos", "Semifinal", "Final", "Tercer puesto"]
ESTADOS_PARTIDO = ["Programado", "Finalizado", "Suspendido", "Reprogramado", "Cancelado", "Walkover"]


def _orden_fixture():
    """Categoría, próximos primero y partidos pasados al final."""
    es_futuro = Partido.fecha >= date.today()
    return (
        Categoria.edad_min.asc(),
        Categoria.nombre.asc(),
        case((es_futuro, 0), else_=1).asc(),
        case((es_futuro, Partido.fecha), else_=None).asc(),
        case((es_futuro, None), else_=Partido.fecha).desc(),
        Partido.hora.asc(),
        Partido.jornada.asc(),
        Partido.orden_llave.asc(),
        Partido.id_partido.asc(),
    )


def _datos_campeonato_formulario():
    fecha_inicio = fecha_iso(request.form.get("fecha_inicio"), "Fecha de inicio")
    fecha_fin = fecha_iso(request.form.get("fecha_fin"), "Fecha de fin", requerida=False)
    rango_fechas(fecha_inicio, fecha_fin, "Fecha de inicio", "Fecha de fin")
    nombre_lugar = texto_opcional(request.form.get("lugar"), "Lugar", 150)
    lugar_catalogo = Lugar.query.filter(
        db.func.lower(Lugar.nombre) == nombre_lugar.lower()
    ).first() if nombre_lugar else None
    return {
        "nombre": texto_requerido(request.form.get("nombre"), "Nombre", 150),
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "lugar": nombre_lugar,
        "id_lugar": lugar_catalogo.id_lugar if lugar_catalogo else None,
        "estado": opcion(
            request.form.get("estado", "Planificado"),
            ESTADOS_CAMPEONATO,
            "Estado",
        ),
        "formato": opcion(
            request.form.get("formato", "Liga"), FORMATOS_CAMPEONATO, "Formato"
        ),
        "vueltas": entero(request.form.get("vueltas", 1), "Vueltas", 1, 2, requerido=True),
        "clasificados": entero(
            request.form.get("clasificados", 4), "Clasificados", 2, 8, requerido=True
        ),
        "puntos_victoria": entero(
            request.form.get("puntos_victoria", 3), "Puntos por victoria", 0, 10, requerido=True
        ),
        "puntos_empate": entero(
            request.form.get("puntos_empate", 1), "Puntos por empate", 0, 10, requerido=True
        ),
        "puntos_derrota": entero(
            request.form.get("puntos_derrota", 0), "Puntos por derrota", 0, 10, requerido=True
        ),
        "tercer_puesto": request.form.get("tercer_puesto") == "1",
    }


def _selecciones_campeonato():
    try:
        ids_categorias = {
            int(valor) for valor in request.form.getlist("categorias")
        }
        ids_equipos = {
            int(valor) for valor in request.form.getlist("equipos")
        }
    except (TypeError, ValueError):
        raise ErrorValidacion("La selección de categorías o equipos no es válida.")
    if not ids_categorias:
        raise ErrorValidacion("Seleccione al menos una categoría para el campeonato.")
    categorias = Categoria.query.filter(
        Categoria.id_categoria.in_(ids_categorias)
    ).all()
    if len(categorias) != len(ids_categorias):
        raise ErrorValidacion("Una de las categorías seleccionadas no existe.")
    equipos = (
        Equipo.query.filter(Equipo.id_equipo.in_(ids_equipos)).all()
        if ids_equipos else []
    )
    if len(equipos) != len(ids_equipos):
        raise ErrorValidacion("Uno de los equipos seleccionados no existe.")
    incompatibles = [
        equipo.nombre for equipo in equipos
        if equipo.id_categoria is not None
        and equipo.id_categoria not in ids_categorias
    ]
    if incompatibles:
        raise ErrorValidacion(
            "Estos participantes no corresponden a las categorías elegidas: "
            + ", ".join(incompatibles)
        )
    return categorias, equipos


def _crear_evento_partido(partido):
    evento = EventoAgenda.query.filter_by(id_partido=partido.id_partido).first()
    if evento is None:
        evento = EventoAgenda(id_partido=partido.id_partido, tipo="Partido")
        db.session.add(evento)
    evento.fecha = partido.fecha
    evento.hora = partido.hora
    evento.descripcion = f"Partido vs {partido.rival}"
    evento.lugar = partido.cancha
    evento.id_lugar = partido.id_lugar
    evento.id_categoria = partido.id_categoria
    evento.id_equipo = partido.id_equipo


def _eliminar_evento_partido(partido):
    EventoAgenda.query.filter_by(id_partido=partido.id_partido).delete()


def _equipos_categoria(campeonato, id_categoria):
    return sorted([
        equipo for equipo in campeonato.equipos
        if equipo.id_categoria is None or equipo.id_categoria == id_categoria
    ], key=lambda equipo: (equipo.es_rival, equipo.nombre.lower()))


def _config_categoria(campeonato, id_categoria):
    config = CampeonatoCategoriaConfig.query.filter_by(
        id_campeonato=campeonato.id_campeonato, id_categoria=id_categoria
    ).first()
    if config is None:
        config = CampeonatoCategoriaConfig(
            id_campeonato=campeonato.id_campeonato,
            id_categoria=id_categoria,
            formato=campeonato.formato,
            vueltas=campeonato.vueltas,
            clasificados=campeonato.clasificados,
            tercer_puesto=campeonato.tercer_puesto,
        )
        db.session.add(config)
    return config


def _sincronizar_configuraciones(campeonato):
    ids = {categoria.id_categoria for categoria in campeonato.categorias}
    CampeonatoCategoriaConfig.query.filter(
        CampeonatoCategoriaConfig.id_campeonato == campeonato.id_campeonato,
        ~CampeonatoCategoriaConfig.id_categoria.in_(ids) if ids else db.true(),
    ).delete(synchronize_session=False)
    for id_categoria in ids:
        _config_categoria(campeonato, id_categoria)


def _jornadas_round_robin(equipos):
    """Algoritmo circular: distribuye los cruces en jornadas reales."""
    participantes = list(equipos)
    if len(participantes) % 2:
        participantes.append(None)
    if len(participantes) < 2:
        return []
    jornadas = []
    for _ in range(len(participantes) - 1):
        cruces = []
        mitad = len(participantes) // 2
        for indice in range(mitad):
            local = participantes[indice]
            visita = participantes[-indice - 1]
            if local is not None and visita is not None:
                cruces.append((local, visita))
        jornadas.append(cruces)
        participantes = [participantes[0], participantes[-1], *participantes[1:-1]]
    return jornadas


def _partido_desde_formulario(campeonato, partido=None):
    try:
        id_categoria = entero(request.form.get("id_categoria"), "Categoría", 1, requerido=True)
        id_local = entero(request.form.get("id_equipo"), "Equipo local", 1, requerido=True)
        id_visita = entero(request.form.get("id_equipo_rival"), "Equipo visitante", 1, requerido=True)
        if id_local == id_visita:
            raise ErrorValidacion("El equipo local y el visitante deben ser diferentes.")
        categoria = next(
            (c for c in campeonato.categorias if c.id_categoria == id_categoria), None
        )
        if categoria is None:
            raise ErrorValidacion("La categoría no pertenece al campeonato.")
        permitidos = {e.id_equipo: e for e in _equipos_categoria(campeonato, id_categoria)}
        if id_local not in permitidos or id_visita not in permitidos:
            raise ErrorValidacion("Ambos equipos deben participar en esta categoría.")
        nombre_cancha = texto_opcional(request.form.get("cancha"), "Cancha", 150)
        lugar_catalogo = Lugar.query.filter(
            db.func.lower(Lugar.nombre) == nombre_cancha.lower()
        ).first() if nombre_cancha else None
        datos = {
            "fecha": fecha_iso(request.form.get("fecha"), "Fecha"),
            "hora": datetime.strptime(request.form["hora"], "%H:%M").time()
            if request.form.get("hora") else None,
            "cancha": nombre_cancha,
            "id_lugar": lugar_catalogo.id_lugar if lugar_catalogo else None,
            "id_categoria": id_categoria,
            "id_equipo": id_local,
            "id_equipo_rival": id_visita,
            "rival": permitidos[id_visita].nombre,
            "fase": opcion(request.form.get("fase", "Liga"), FASES, "Fase"),
            "grupo": texto_opcional(request.form.get("grupo"), "Grupo", 30),
            "jornada": entero(request.form.get("jornada"), "Jornada", 1, 999),
            "orden_llave": entero(request.form.get("orden_llave"), "Orden de llave", 1, 99),
            "estado_partido": opcion(
                request.form.get("estado_partido", "Programado"),
                ESTADOS_PARTIDO, "Estado del partido",
            ),
            "observacion": texto_opcional(request.form.get("observacion"), "Observación", 255),
        }
    except (ValueError, KeyError):
        raise ErrorValidacion("La hora indicada no es válida.")
    duplicado = es_duplicado_partido(
        datos["fecha"], datos["hora"], id_local, id_visita, datos["rival"],
        partido.id_partido if partido else None,
    )
    if duplicado:
        raise ErrorValidacion(f"Ya existe el partido #{duplicado.id_partido} con esos equipos, fecha y hora.")
    conflictos = detectar_conflictos(
        datos["fecha"], datos["hora"], datos["id_lugar"], datos["cancha"],
        id_local, id_visita, partido.id_partido if partido else None,
    )
    if conflictos:
        usuario = getattr(g, "usuario_actual", None)
        motivo = request.form.get("motivo_conflicto", "").strip()
        if not (request.form.get("autorizar_conflicto") == "1" and motivo and usuario and usuario.tiene_permiso("administrar")):
            raise ErrorValidacion("Conflicto de horario: " + "; ".join(f"{t}: {r}" for t, r in conflictos))
    if partido is None:
        partido = Partido(id_campeonato=campeonato.id_campeonato)
        db.session.add(partido)
    for campo, valor in datos.items():
        setattr(partido, campo, valor)
    db.session.flush()
    for tipo, referencia in conflictos:
        db.session.add(ConflictoAutorizado(
            tipo_entidad="Partido", id_entidad=partido.id_partido,
            tipo_conflicto=tipo, referencia=referencia,
            motivo=request.form.get("motivo_conflicto", "").strip(),
            id_usuario=g.usuario_actual.id_usuario,
        ))
    _crear_evento_partido(partido)
    return partido


def _recalcular_posiciones(id_campeonato):
    """Reconstruye la tabla desde resultados; corregir un marcador no duplica datos."""
    posiciones = Posicion.query.filter_by(id_campeonato=id_campeonato).all()
    mapa = {}
    for posicion in posiciones:
        posicion.pj = posicion.pg = posicion.pe = posicion.pp = 0
        posicion.gf = posicion.gc = 0
        mapa[(posicion.id_categoria, posicion.id_equipo)] = posicion

    partidos = Partido.query.filter(
        Partido.id_campeonato == id_campeonato,
        Partido.estado_partido.in_(["Finalizado", "Walkover"]),
        Partido.fase.in_(["Liga", "Grupos"]),
    ).all()
    for partido in partidos:
        if partido.goles_local is None or partido.goles_visita is None:
            continue
        goles_local, goles_visita = partido.goles_local, partido.goles_visita
        id_visita = partido.id_equipo_rival
        if id_visita is None:
            equipo_visita = Equipo.query.filter(
                db.func.lower(Equipo.nombre) == partido.rival.lower()
            ).first()
            id_visita = equipo_visita.id_equipo if equipo_visita else None
        local = mapa.get((partido.id_categoria, partido.id_equipo))
        visita = mapa.get((partido.id_categoria, id_visita))
        for posicion, favor, contra in (
            (local, goles_local, goles_visita),
            (visita, goles_visita, goles_local),
        ):
            if posicion is None:
                continue
            posicion.pj += 1
            posicion.gf += favor
            posicion.gc += contra
            if favor > contra:
                posicion.pg += 1
            elif favor == contra:
                posicion.pe += 1
            else:
                posicion.pp += 1


@bp.route("/")
def listar():
    campeonatos = Campeonato.query.order_by(Campeonato.fecha_inicio.desc()).all()
    return render_template("campeonatos/listar.html", campeonatos=campeonatos)


@bp.route("/rivales")
def rivales():
    equipos_rivales = (
        Equipo.query.filter_by(es_rival=True)
        .order_by(Equipo.nombre, Equipo.id_categoria)
        .all()
    )
    return render_template(
        "campeonatos/rivales.html", rivales=equipos_rivales
    )


@bp.route("/rivales/nuevo", methods=["GET", "POST"])
def crear_rival():
    categorias = Categoria.query.order_by(Categoria.edad_min, Categoria.nombre).all()
    if request.method == "POST":
        try:
            nombre = texto_requerido(request.form.get("nombre"), "Nombre del rival", 120)
            id_categoria = entero(
                request.form.get("id_categoria"), "Categoría", 1
            )
            if id_categoria and db.session.get(Categoria, id_categoria) is None:
                raise ErrorValidacion("La categoría seleccionada no existe.")
            repetido = Equipo.query.filter(
                db.func.lower(Equipo.nombre) == nombre.lower(),
                Equipo.id_categoria == id_categoria,
                Equipo.es_rival.is_(True),
            ).first()
            if repetido:
                raise ErrorValidacion(
                    "Ese rival ya está registrado en la categoría seleccionada."
                )
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "campeonatos/rival_form.html",
                rival=None,
                categorias=categorias,
            )
        rival = Equipo(
            nombre=nombre,
            id_categoria=id_categoria,
            es_rival=True,
        )
        db.session.add(rival)
        db.session.commit()
        flash(f"Rival '{rival.nombre}' registrado correctamente.", "success")
        return redirect(url_for("campeonatos.rivales"))
    return render_template(
        "campeonatos/rival_form.html", rival=None, categorias=categorias
    )


@bp.route("/rivales/<int:id_rival>/editar", methods=["GET", "POST"])
def editar_rival(id_rival):
    rival = Equipo.query.filter_by(id_equipo=id_rival, es_rival=True).first_or_404()
    categorias = Categoria.query.order_by(Categoria.edad_min, Categoria.nombre).all()
    if request.method == "POST":
        try:
            nombre = texto_requerido(request.form.get("nombre"), "Nombre del rival", 120)
            id_categoria = entero(
                request.form.get("id_categoria"), "Categoría", 1
            )
            if id_categoria and db.session.get(Categoria, id_categoria) is None:
                raise ErrorValidacion("La categoría seleccionada no existe.")
            if rival.campeonatos and id_categoria != rival.id_categoria:
                raise ErrorValidacion(
                    "No se puede cambiar la categoría porque el rival ya participa "
                    "en un campeonato. Puede cambiar únicamente el nombre."
                )
            repetido = Equipo.query.filter(
                db.func.lower(Equipo.nombre) == nombre.lower(),
                Equipo.id_categoria == id_categoria,
                Equipo.es_rival.is_(True),
                Equipo.id_equipo != rival.id_equipo,
            ).first()
            if repetido:
                raise ErrorValidacion(
                    "Ese rival ya está registrado en la categoría seleccionada."
                )
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "campeonatos/rival_form.html",
                rival=rival,
                categorias=categorias,
            )
        rival.nombre = nombre
        rival.id_categoria = id_categoria
        db.session.commit()
        flash("Rival actualizado correctamente.", "success")
        return redirect(url_for("campeonatos.rivales"))
    return render_template(
        "campeonatos/rival_form.html", rival=rival, categorias=categorias
    )


@bp.route("/rivales/<int:id_rival>/eliminar", methods=["POST"])
def eliminar_rival(id_rival):
    rival = Equipo.query.filter_by(id_equipo=id_rival, es_rival=True).first_or_404()
    esta_en_uso = (
        bool(rival.campeonatos)
        or Partido.query.filter(
            db.or_(
                Partido.id_equipo == rival.id_equipo,
                Partido.id_equipo_rival == rival.id_equipo,
            )
        ).first() is not None
        or Posicion.query.filter_by(id_equipo=rival.id_equipo).first() is not None
    )
    if esta_en_uso:
        flash(
            "No se puede eliminar: el rival ya tiene campeonatos, partidos "
            "o posiciones asociados.",
            "danger",
        )
        return redirect(url_for("campeonatos.rivales"))
    db.session.delete(rival)
    db.session.commit()
    flash("Rival eliminado.", "success")
    return redirect(url_for("campeonatos.rivales"))


@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    rivales = Equipo.query.filter_by(es_rival=True).order_by(Equipo.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()

    if request.method == "POST":
        try:
            datos = _datos_campeonato_formulario()
            categorias_seleccionadas, equipos_seleccionados = _selecciones_campeonato()
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "campeonatos/form.html", campeonato=None, categorias=categorias,
                equipos=equipos, rivales=rivales, lugares=lugares,
                estados=ESTADOS_CAMPEONATO, formatos=FORMATOS_CAMPEONATO,
            )
        campeonato = Campeonato(**datos)
        campeonato.categorias = categorias_seleccionadas
        campeonato.equipos = equipos_seleccionados

        db.session.add(campeonato)
        db.session.flush()
        _sincronizar_configuraciones(campeonato)
        db.session.add(Auditoria(
            modulo="Campeonatos", accion="Crear", entidad="Campeonato",
            id_entidad=campeonato.id_campeonato, detalle=campeonato.nombre,
        ))
        db.session.commit()
        flash(f"Campeonato '{campeonato.nombre}' creado.", "success")
        return redirect(url_for("campeonatos.detalle", id_campeonato=campeonato.id_campeonato))

    return render_template(
        "campeonatos/form.html", campeonato=None, categorias=categorias,
        equipos=equipos, rivales=rivales, lugares=lugares,
        estados=ESTADOS_CAMPEONATO, formatos=FORMATOS_CAMPEONATO,
    )


@bp.route("/<int:id_campeonato>")
def detalle(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    configuraciones = {
        categoria.id_categoria: _config_categoria(campeonato, categoria.id_categoria)
        for categoria in campeonato.categorias
    }
    posiciones_por_categoria = {}
    for cat in campeonato.categorias:
        filas = (
            Posicion.query.filter_by(id_campeonato=id_campeonato, id_categoria=cat.id_categoria)
            .all()
        )
        filas.sort(key=lambda p: (-p.pts, -p.dg, -p.gf))
        posiciones_por_categoria[cat] = filas

    consulta_partidos = Partido.query.filter_by(id_campeonato=id_campeonato)
    id_categoria_filtro = request.args.get("id_categoria", type=int)
    fase_filtro = request.args.get("fase", "").strip()
    if id_categoria_filtro:
        consulta_partidos = consulta_partidos.filter_by(id_categoria=id_categoria_filtro)
    if fase_filtro in FASES:
        consulta_partidos = consulta_partidos.filter_by(fase=fase_filtro)
    partidos = consulta_partidos.join(Categoria).order_by(*_orden_fixture()).all()
    todos_partidos = Partido.query.filter_by(id_campeonato=id_campeonato).all()
    finalizados = sum(p.estado_partido == "Finalizado" for p in todos_partidos)
    progreso = round(finalizados * 100 / len(todos_partidos)) if todos_partidos else 0
    eliminatorias = {
        fase: [p for p in todos_partidos if p.fase == fase]
        for fase in ["Cuartos", "Semifinal", "Final", "Tercer puesto"]
    }
    campeones = []
    for final in eliminatorias["Final"]:
        if final.ganador_id:
            campeones.append((final.categoria, db.session.get(Equipo, final.ganador_id)))
    participantes_por_categoria = {
        categoria: [
            equipo for equipo in campeonato.equipos
            if equipo.id_categoria is None
            or equipo.id_categoria == categoria.id_categoria
        ]
        for categoria in campeonato.categorias
    }
    return render_template(
        "campeonatos/detalle.html", campeonato=campeonato,
        posiciones_por_categoria=posiciones_por_categoria, partidos=partidos,
        participantes_por_categoria=participantes_por_categoria,
        progreso=progreso, total_partidos=len(todos_partidos), finalizados=finalizados,
        eliminatorias=eliminatorias, fases=FASES, filtros=request.args,
        campeones=campeones,
        configuraciones=configuraciones, formatos=FORMATOS_CAMPEONATO,
        podios=campeonato.podios,
    )


@bp.route("/<int:id_campeonato>/editar", methods=["GET", "POST"])
def editar(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    rivales = Equipo.query.filter_by(es_rival=True).order_by(Equipo.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()

    if request.method == "POST":
        try:
            datos = _datos_campeonato_formulario()
            categorias_seleccionadas, equipos_seleccionados = _selecciones_campeonato()
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "campeonatos/form.html", campeonato=campeonato, categorias=categorias,
                equipos=equipos, rivales=rivales, lugares=lugares,
                estados=ESTADOS_CAMPEONATO, formatos=FORMATOS_CAMPEONATO,
            )
        tiene_partidos = Partido.query.filter_by(id_campeonato=id_campeonato).first() is not None
        ids_categorias_actuales = {c.id_categoria for c in campeonato.categorias}
        ids_equipos_actuales = {e.id_equipo for e in campeonato.equipos}
        ids_categorias_nuevos = {c.id_categoria for c in categorias_seleccionadas}
        ids_equipos_nuevos = {e.id_equipo for e in equipos_seleccionados}
        if tiene_partidos and (
            ids_categorias_actuales != ids_categorias_nuevos
            or ids_equipos_actuales != ids_equipos_nuevos
        ):
            flash(
                "No se pueden cambiar categorías o participantes después de crear "
                "el fixture. Edite los partidos o cree otro campeonato.",
                "danger",
            )
            return redirect(url_for("campeonatos.editar", id_campeonato=id_campeonato))
        for campo, valor in datos.items():
            setattr(campeonato, campo, valor)

        campeonato.categorias = categorias_seleccionadas
        campeonato.equipos = equipos_seleccionados
        _sincronizar_configuraciones(campeonato)
        db.session.add(Auditoria(
            modulo="Campeonatos", accion="Editar", entidad="Campeonato",
            id_entidad=id_campeonato, detalle=campeonato.nombre,
        ))
        db.session.commit()
        flash("Campeonato actualizado.", "success")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))

    return render_template(
        "campeonatos/form.html", campeonato=campeonato, categorias=categorias,
        equipos=equipos, rivales=rivales, lugares=lugares,
        estados=ESTADOS_CAMPEONATO, formatos=FORMATOS_CAMPEONATO,
    )


@bp.route("/<int:id_campeonato>/generar-fixture", methods=["POST"])
def generar_fixture(id_campeonato):
    """Genera el fixture completo (todos contra todos) por cada categoría del
    campeonato, usando los equipos globales inscritos en el campeonato."""
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    existentes = Partido.query.filter_by(id_campeonato=id_campeonato).all()
    if campeonato.estado in {"Finalizado", "Cancelado"}:
        flash("Un campeonato cerrado no puede regenerar su fixture.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    if any(p.estado_partido == "Finalizado" or p.resultado for p in existentes):
        flash(
            "El fixture no se reemplazó porque ya existen resultados. "
            "Puede editar o agregar los encuentros manualmente.",
            "danger",
        )
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))

    # Limpia también los eventos vinculados; no deja Agenda huérfana.
    ids_partidos = [
        fila[0] for fila in db.session.query(Partido.id_partido)
        .filter_by(id_campeonato=id_campeonato).all()
    ]
    if ids_partidos:
        EventoAgenda.query.filter(EventoAgenda.id_partido.in_(ids_partidos)).delete(
            synchronize_session=False
        )
    Partido.query.filter_by(id_campeonato=id_campeonato).delete()
    Posicion.query.filter_by(id_campeonato=id_campeonato).delete()
    db.session.flush()

    total_generados = 0

    for categoria in campeonato.categorias:
        config_categoria = _config_categoria(campeonato, categoria.id_categoria)
        equipos_categoria = _equipos_categoria(campeonato, categoria.id_categoria)
        if config_categoria.formato in {"Manual", "Eliminación directa"}:
            continue
        for equipo in equipos_categoria:
            db.session.add(Posicion(
                id_campeonato=id_campeonato, id_categoria=categoria.id_categoria,
                id_equipo=equipo.id_equipo,
            ))
        jornadas = _jornadas_round_robin(equipos_categoria)
        for vuelta in range(config_categoria.vueltas):
            for numero, cruces in enumerate(jornadas, 1):
                fecha_jornada = campeonato.fecha_inicio + timedelta(
                    days=(vuelta * len(jornadas) + numero - 1) * 7
                )
                for local, visita in cruces:
                    if vuelta % 2:
                        local, visita = visita, local
                    partido = Partido(
                        fecha=fecha_jornada,
                        cancha=campeonato.lugar, id_lugar=campeonato.id_lugar,
                        id_equipo=local.id_equipo,
                        id_equipo_rival=visita.id_equipo,
                        id_categoria=categoria.id_categoria,
                        rival=visita.nombre,
                        id_campeonato=id_campeonato,
                        fase="Liga",
                        jornada=vuelta * len(jornadas) + numero,
                        estado_partido="Programado",
                    )
                    db.session.add(partido)
                    db.session.flush()
                    _crear_evento_partido(partido)
                    total_generados += 1

    db.session.commit()
    if total_generados == 0:
            flash("No se generaron partidos: asigne al menos 2 equipos compatibles y una categoría al campeonato.", "warning")
    else:
        flash(f"Fixture generado: {total_generados} partidos programados.", "success")
    return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))


@bp.route("/<int:id_campeonato>/categorias/<int:id_categoria>/configurar", methods=["POST"])
def configurar_categoria(id_campeonato, id_categoria):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    if Partido.query.filter_by(
        id_campeonato=id_campeonato, id_categoria=id_categoria
    ).first():
        flash("No se puede cambiar el formato de una categoría con partidos creados.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    if id_categoria not in {c.id_categoria for c in campeonato.categorias}:
        flash("La categoría no pertenece al campeonato.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    try:
        config = _config_categoria(campeonato, id_categoria)
        config.formato = opcion(
            request.form.get("formato"), FORMATOS_CAMPEONATO, "Formato"
        )
        config.vueltas = entero(request.form.get("vueltas"), "Vueltas", 1, 2, requerido=True)
        config.clasificados = entero(
            request.form.get("clasificados"), "Clasificados", 2, 8, requerido=True
        )
        if config.clasificados not in {2, 4, 8}:
            raise ErrorValidacion("Los clasificados deben ser 2, 4 u 8.")
        config.tercer_puesto = request.form.get("tercer_puesto") == "1"
    except ErrorValidacion as error:
        flash(str(error), "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    db.session.add(Auditoria(
        modulo="Campeonatos", accion="Configurar categoría",
        entidad="Campeonato", id_entidad=id_campeonato,
        detalle=f"categoria={id_categoria}; formato={config.formato}",
    ))
    db.session.commit()
    flash("Configuración de categoría actualizada.", "success")
    return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))


@bp.route("/<int:id_campeonato>/partidos/nuevo", methods=["GET", "POST"])
def crear_partido_manual(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    if campeonato.estado in {"Finalizado", "Cancelado"}:
        flash("El campeonato está cerrado.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    if request.method == "POST":
        try:
            _partido_desde_formulario(campeonato)
            _asegurar_posiciones(campeonato)
            db.session.commit()
            flash("Partido agregado al fixture.", "success")
            return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
        except ErrorValidacion as error:
            db.session.rollback()
            flash(str(error), "danger")
    return render_template(
        "campeonatos/partido_form.html", campeonato=campeonato, partido=None,
        fases=FASES, estados_partido=ESTADOS_PARTIDO,
        participantes={c.id_categoria: _equipos_categoria(campeonato, c.id_categoria)
                       for c in campeonato.categorias},
        lugares=Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all(),
    )


@bp.route("/<int:id_campeonato>/partidos/<int:id_partido>/editar", methods=["GET", "POST"])
def editar_partido_manual(id_campeonato, id_partido):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    partido = Partido.query.filter_by(
        id_partido=id_partido, id_campeonato=id_campeonato
    ).first_or_404()
    if campeonato.estado in {"Finalizado", "Cancelado"}:
        flash("Reabra el campeonato antes de modificarlo.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    if partido.estado_partido == "Finalizado":
        flash(
            "Un partido finalizado no puede cambiar equipos, fase o fecha. "
            "Corrija únicamente su marcador desde el fixture.",
            "danger",
        )
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    if request.method == "POST":
        try:
            _partido_desde_formulario(campeonato, partido)
            _asegurar_posiciones(campeonato)
            _recalcular_posiciones(id_campeonato)
            db.session.commit()
            flash("Partido actualizado.", "success")
            return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
        except ErrorValidacion as error:
            db.session.rollback()
            flash(str(error), "danger")
    return render_template(
        "campeonatos/partido_form.html", campeonato=campeonato, partido=partido,
        fases=FASES, estados_partido=ESTADOS_PARTIDO,
        participantes={c.id_categoria: _equipos_categoria(campeonato, c.id_categoria)
                       for c in campeonato.categorias},
        lugares=Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all(),
    )


@bp.route("/<int:id_campeonato>/partidos/<int:id_partido>/eliminar", methods=["POST"])
def eliminar_partido_manual(id_campeonato, id_partido):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    partido = Partido.query.filter_by(
        id_partido=id_partido, id_campeonato=id_campeonato
    ).first_or_404()
    if campeonato.estado in {"Finalizado", "Cancelado"}:
        flash("El campeonato está cerrado.", "danger")
    elif partido.estado_partido == "Finalizado":
        flash("Quite primero el resultado antes de eliminar el partido.", "danger")
    else:
        _eliminar_evento_partido(partido)
        db.session.delete(partido)
        db.session.commit()
        flash("Partido eliminado del fixture.", "success")
    return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))


def _asegurar_posiciones(campeonato):
    existentes = {
        (p.id_categoria, p.id_equipo)
        for p in Posicion.query.filter_by(id_campeonato=campeonato.id_campeonato).all()
    }
    for categoria in campeonato.categorias:
        for equipo in _equipos_categoria(campeonato, categoria.id_categoria):
            clave = (categoria.id_categoria, equipo.id_equipo)
            if clave not in existentes:
                db.session.add(Posicion(
                    id_campeonato=campeonato.id_campeonato,
                    id_categoria=categoria.id_categoria,
                    id_equipo=equipo.id_equipo,
                ))
                existentes.add(clave)


@bp.route("/<int:id_campeonato>/eliminatorias/generar", methods=["POST"])
def generar_eliminatorias(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    if campeonato.estado in {"Finalizado", "Cancelado"}:
        flash("El campeonato está cerrado.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    id_categoria = request.form.get("id_categoria", type=int)
    categoria = next((c for c in campeonato.categorias if c.id_categoria == id_categoria), None)
    if categoria is None:
        flash("Seleccione una categoría válida.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    if Partido.query.filter(
        Partido.id_campeonato == id_campeonato,
        Partido.id_categoria == id_categoria,
        Partido.fase.in_(["Cuartos", "Semifinal", "Final"]),
    ).first():
        flash("La categoría ya tiene una fase eliminatoria.", "warning")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))

    posiciones = Posicion.query.filter_by(
        id_campeonato=id_campeonato, id_categoria=id_categoria
    ).all()
    posiciones.sort(key=lambda p: (-p.pts, -p.dg, -p.gf))
    config_categoria = _config_categoria(campeonato, id_categoria)
    equipos = [p.equipo for p in posiciones][:config_categoria.clasificados]
    if not equipos:
        equipos = _equipos_categoria(campeonato, id_categoria)
    if len(equipos) < 2:
        flash("Se necesitan al menos dos equipos para crear una eliminatoria.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    cantidad = 8 if len(equipos) >= 8 else 4 if len(equipos) >= 4 else 2
    equipos = equipos[:cantidad]
    fase = "Cuartos" if cantidad == 8 else "Semifinal" if cantidad == 4 else "Final"
    fecha = max(
        [p.fecha for p in Partido.query.filter_by(id_campeonato=id_campeonato).all()]
        or [campeonato.fecha_inicio]
    ) + timedelta(days=7)
    for indice in range(cantidad // 2):
        local, visita = equipos[indice], equipos[-indice - 1]
        partido = Partido(
            fecha=fecha, cancha=campeonato.lugar, id_lugar=campeonato.id_lugar, id_equipo=local.id_equipo,
            id_equipo_rival=visita.id_equipo, id_categoria=id_categoria,
            rival=visita.nombre, id_campeonato=id_campeonato, fase=fase,
            orden_llave=indice + 1, estado_partido="Programado",
        )
        db.session.add(partido)
        db.session.flush()
        _crear_evento_partido(partido)
    db.session.commit()
    flash(f"Fase {fase} creada con los mejores {cantidad} equipos.", "success")
    return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))


def _avanzar_eliminatoria(partido):
    if not partido.es_eliminatorio or partido.ganador_id is None or partido.fase == "Final":
        return
    orden_siguiente = ((partido.orden_llave or 1) + 1) // 2
    fase_siguiente = {"Cuartos": "Semifinal", "Semifinal": "Final"}.get(partido.fase)
    if not fase_siguiente:
        return
    partidos_fase = Partido.query.filter_by(
        id_campeonato=partido.id_campeonato,
        id_categoria=partido.id_categoria,
        fase=partido.fase,
    ).all()
    pareja = [p for p in partidos_fase if ((p.orden_llave or 1) + 1) // 2 == orden_siguiente]
    if len(pareja) != 2 or any(p.ganador_id is None for p in pareja):
        return
    siguiente = Partido.query.filter_by(
        id_campeonato=partido.id_campeonato, id_categoria=partido.id_categoria,
        fase=fase_siguiente, orden_llave=orden_siguiente,
    ).first()
    ganadores = [db.session.get(Equipo, p.ganador_id) for p in sorted(pareja, key=lambda p: p.orden_llave)]
    if siguiente is None:
        siguiente = Partido(
            fecha=max(p.fecha for p in pareja) + timedelta(days=7),
            cancha=partido.campeonato.lugar, id_lugar=partido.campeonato.id_lugar, id_categoria=partido.id_categoria,
            id_campeonato=partido.id_campeonato, fase=fase_siguiente,
            orden_llave=orden_siguiente, estado_partido="Programado",
        )
        db.session.add(siguiente)
    siguiente.id_equipo = ganadores[0].id_equipo
    siguiente.id_equipo_rival = ganadores[1].id_equipo
    siguiente.rival = ganadores[1].nombre
    pareja_ordenada = sorted(pareja, key=lambda p: p.orden_llave)
    siguiente.id_partido_origen_local = pareja_ordenada[0].id_partido
    siguiente.id_partido_origen_visita = pareja_ordenada[1].id_partido
    db.session.flush()
    _crear_evento_partido(siguiente)
    config_categoria = _config_categoria(partido.campeonato, partido.id_categoria)
    if partido.fase == "Semifinal" and config_categoria.tercer_puesto:
        perdedores = []
        for semifinal in sorted(pareja, key=lambda p: p.orden_llave):
            perdedor_id = (
                semifinal.id_equipo_rival
                if semifinal.ganador_id == semifinal.id_equipo
                else semifinal.id_equipo
            )
            perdedores.append(db.session.get(Equipo, perdedor_id))
        tercer_puesto = Partido.query.filter_by(
            id_campeonato=partido.id_campeonato,
            id_categoria=partido.id_categoria,
            fase="Tercer puesto",
        ).first()
        if tercer_puesto is None:
            tercer_puesto = Partido(
                fecha=max(p.fecha for p in pareja) + timedelta(days=7),
                cancha=partido.campeonato.lugar, id_lugar=partido.campeonato.id_lugar,
                id_categoria=partido.id_categoria,
                id_campeonato=partido.id_campeonato,
                fase="Tercer puesto", orden_llave=1,
                estado_partido="Programado",
            )
            db.session.add(tercer_puesto)
        tercer_puesto.id_equipo = perdedores[0].id_equipo
        tercer_puesto.id_equipo_rival = perdedores[1].id_equipo
        tercer_puesto.rival = perdedores[1].nombre
        tercer_puesto.id_partido_origen_local = pareja_ordenada[0].id_partido
        tercer_puesto.id_partido_origen_visita = pareja_ordenada[1].id_partido
        db.session.flush()
        _crear_evento_partido(tercer_puesto)


@bp.route("/<int:id_campeonato>/finalizar", methods=["POST"])
def finalizar(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    pendientes = Partido.query.filter_by(id_campeonato=id_campeonato).filter(
        Partido.estado_partido.notin_(["Finalizado", "Cancelado", "Walkover"])
    ).count()
    forzar = request.form.get("forzar") == "1"
    if pendientes and not forzar:
        flash(
            f"Quedan {pendientes} partidos pendientes. Confirme el cierre forzado si corresponde.",
            "danger",
        )
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    podios_nuevos = []
    categorias_sin_campeon = []
    for categoria in campeonato.categorias:
        final = Partido.query.filter_by(
            id_campeonato=id_campeonato,
            id_categoria=categoria.id_categoria,
            fase="Final",
        ).order_by(Partido.id_partido.desc()).first()
        campeon_id = subcampeon_id = tercero_id = None
        if final and final.ganador_id:
            campeon_id = final.ganador_id
            subcampeon_id = (
                final.id_equipo_rival if campeon_id == final.id_equipo else final.id_equipo
            )
            tercer_partido = Partido.query.filter_by(
                id_campeonato=id_campeonato,
                id_categoria=categoria.id_categoria,
                fase="Tercer puesto",
            ).first()
            if tercer_partido and tercer_partido.ganador_id:
                tercero_id = tercer_partido.ganador_id
        else:
            posiciones = Posicion.query.filter_by(
                id_campeonato=id_campeonato, id_categoria=categoria.id_categoria
            ).all()
            posiciones.sort(key=lambda p: (-p.pts, -p.dg, -p.gf))
            posiciones = [p for p in posiciones if p.pj > 0]
            if posiciones:
                campeon_id = posiciones[0].id_equipo
                subcampeon_id = posiciones[1].id_equipo if len(posiciones) > 1 else None
                tercero_id = posiciones[2].id_equipo if len(posiciones) > 2 else None
        if campeon_id is None:
            categorias_sin_campeon.append(categoria.nombre_mostrado)
            continue
        podio = PodioCampeonato.query.filter_by(
            id_campeonato=id_campeonato, id_categoria=categoria.id_categoria
        ).first() or PodioCampeonato(
            id_campeonato=id_campeonato, id_categoria=categoria.id_categoria
        )
        podio.id_campeon = campeon_id
        podio.id_subcampeon = subcampeon_id
        podio.id_tercero = tercero_id
        podios_nuevos.append(podio)
    if categorias_sin_campeon and request.form.get("sin_campeon") != "1":
        flash(
            "No se puede cerrar: faltan campeones en " + ", ".join(categorias_sin_campeon),
            "danger",
        )
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    for podio in podios_nuevos:
        db.session.add(podio)
    campeonato.estado = "Finalizado"
    campeonato.finalizado_en = datetime.now(timezone.utc).replace(tzinfo=None)
    campeonato.motivo_cierre = texto_opcional(
        request.form.get("motivo"), "Motivo de cierre", 255
    )
    for convocatoria in campeonato.alumnos_habilitados:
        convocatoria.archivado = True
        convocatoria.archivado_en = campeonato.finalizado_en
        convocatoria.habilitado = False
    db.session.add(Auditoria(
        modulo="Campeonatos", accion="Finalizar", entidad="Campeonato",
        id_entidad=id_campeonato, detalle=campeonato.motivo_cierre,
    ))
    db.session.commit()
    flash("Campeonato finalizado. Los convocados quedaron archivados en el historial.", "success")
    return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))


@bp.route("/<int:id_campeonato>/reabrir", methods=["POST"])
def reabrir(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    try:
        motivo = texto_requerido(
            request.form.get("motivo"), "Motivo de reapertura", 255
        )
    except ErrorValidacion as error:
        flash(str(error), "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))
    campeonato.estado = "En curso"
    campeonato.finalizado_en = None
    campeonato.motivo_reapertura = motivo
    PodioCampeonato.query.filter_by(id_campeonato=id_campeonato).delete()
    for convocatoria in campeonato.alumnos_habilitados:
        if convocatoria.archivado:
            convocatoria.archivado = False
            convocatoria.archivado_en = None
            convocatoria.habilitado = True
    db.session.add(Auditoria(
        modulo="Campeonatos", accion="Reabrir", entidad="Campeonato",
        id_entidad=id_campeonato, detalle=motivo,
    ))
    db.session.commit()
    flash("Campeonato reabierto y convocatoria restaurada.", "success")
    return redirect(url_for("campeonatos.detalle", id_campeonato=id_campeonato))


@bp.route("/<int:id_campeonato>/resumen.csv")
def exportar_resumen(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    filas = ["Categoría,Fase,Jornada,Fecha,Local,Visitante,Resultado,Estado"]
    partidos = Partido.query.filter_by(id_campeonato=id_campeonato).order_by(
        Partido.id_categoria, Partido.fecha
    ).all()
    for p in partidos:
        valores = [
            p.categoria.nombre_mostrado, p.fase, p.jornada or "",
            p.fecha.strftime("%d/%m/%Y"), p.equipo.nombre,
            p.equipo_rival.nombre if p.equipo_rival else p.rival,
            p.resultado or "", p.estado_partido,
        ]
        valores = [
            "'" + str(v) if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v
            for v in valores
        ]
        filas.append(",".join(f'"{str(v).replace(chr(34), chr(34) * 2)}"' for v in valores))
    contenido = "\ufeff" + "\n".join(filas)
    guardar_texto(
        contenido, "campeonatos",
        f"campeonato-{campeonato.id_campeonato}.csv",
    )
    return Response(
        contenido, mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="campeonato-{campeonato.id_campeonato}.csv"'},
    )


def _consulta_fixture_exportacion(campeonato):
    consulta = Partido.query.filter_by(id_campeonato=campeonato.id_campeonato)
    id_categoria = request.args.get("id_categoria", type=int)
    fase = request.args.get("fase", "").strip()
    ids_categorias = {categoria.id_categoria for categoria in campeonato.categorias}
    if id_categoria and id_categoria in ids_categorias:
        consulta = consulta.filter_by(id_categoria=id_categoria)
    if fase in FASES:
        consulta = consulta.filter_by(fase=fase)
    return consulta.join(Categoria).order_by(*_orden_fixture()).all()


def _datos_fixture_campeonato(campeonato):
    encabezados = [
        "N°", "Categoría", "Fase", "Jornada", "Fecha", "Hora",
        "Local", "Visitante", "Resultado", "Penales", "Estado", "Cancha",
        "Google Maps",
    ]
    partidos = _consulta_fixture_exportacion(campeonato)
    filas = []
    for numero, p in enumerate(partidos, 1):
        filas.append([
            numero, p.categoria.nombre_mostrado, p.fase, p.jornada or "—",
            p.fecha.strftime("%d/%m/%Y"),
            p.hora.strftime("%H:%M") if p.hora else "—",
            p.equipo.nombre,
            p.equipo_rival.nombre if p.equipo_rival else p.rival,
            p.resultado or "Pendiente",
            f"{p.penales_local}-{p.penales_visita}" if p.penales_local is not None else "—",
            p.estado_partido, p.cancha or "—",
            p.lugar_catalogo.google_maps_url if p.lugar_catalogo and p.lugar_catalogo.google_maps_url else "—",
        ])
    return encabezados, filas


def _datos_posiciones_campeonato(campeonato):
    encabezados = [
        "N°", "Categoría", "Posición", "Equipo", "PJ", "PG", "PE",
        "PP", "GF", "GC", "DG", "Pts",
    ]
    id_categoria = request.args.get("id_categoria", type=int)
    categorias = [
        categoria for categoria in campeonato.categorias
        if not id_categoria or categoria.id_categoria == id_categoria
    ]
    filas = []
    numero = 1
    for categoria in categorias:
        posiciones = Posicion.query.filter_by(
            id_campeonato=campeonato.id_campeonato,
            id_categoria=categoria.id_categoria,
        ).all()
        posiciones.sort(
            key=lambda posicion: (
                -posicion.pts, -posicion.dg, -posicion.gf,
                posicion.equipo.nombre.lower(),
            )
        )
        for puesto, posicion in enumerate(posiciones, 1):
            filas.append([
                numero, categoria.nombre_mostrado, puesto, posicion.equipo.nombre,
                posicion.pj, posicion.pg, posicion.pe, posicion.pp,
                posicion.gf, posicion.gc, posicion.dg, posicion.pts,
            ])
            numero += 1
    return encabezados, filas


def _logo_reporte():
    return configuracion_y_logo()[1]


@bp.route("/<int:id_campeonato>/resumen.xlsx")
def exportar_resumen_excel(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    encabezados, filas = _datos_fixture_campeonato(campeonato)
    buffer = exportar_tabla_excel(
        f"Campeonato {campeonato.nombre}", encabezados, filas,
        logo_path=_logo_reporte(), orientacion="horizontal",
    )
    return enviar_buffer(
        buffer, "campeonatos", f"campeonato-{id_campeonato}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/<int:id_campeonato>/resumen.pdf")
def exportar_resumen_pdf(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    encabezados, filas = _datos_fixture_campeonato(campeonato)
    buffer = generar_tabla_pdf(
        f"Campeonato {campeonato.nombre}", encabezados, filas,
        orientacion="horizontal", tamano_pagina="carta", tamano_letra=8,
        logo_path=_logo_reporte(),
    )
    return enviar_buffer(
        buffer, "campeonatos", f"campeonato-{id_campeonato}.pdf",
        "application/pdf",
    )


@bp.route("/<int:id_campeonato>/fixture.xlsx")
def exportar_fixture_excel(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    encabezados, filas = _datos_fixture_campeonato(campeonato)
    buffer = exportar_tabla_excel(
        f"Fixture - {campeonato.nombre}", encabezados, filas,
        logo_path=_logo_reporte(), orientacion="horizontal",
    )
    return enviar_buffer(
        buffer, "campeonatos", f"fixture-campeonato-{id_campeonato}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/<int:id_campeonato>/fixture.pdf")
def exportar_fixture_pdf(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    encabezados, filas = _datos_fixture_campeonato(campeonato)
    buffer = generar_tabla_pdf(
        f"Fixture - {campeonato.nombre}", encabezados, filas,
        orientacion="horizontal", tamano_pagina="carta", tamano_letra=8,
        logo_path=_logo_reporte(),
    )
    return enviar_buffer(
        buffer, "campeonatos", f"fixture-campeonato-{id_campeonato}.pdf",
        "application/pdf",
    )


@bp.route("/<int:id_campeonato>/posiciones.xlsx")
def exportar_posiciones_excel(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    encabezados, filas = _datos_posiciones_campeonato(campeonato)
    buffer = exportar_tabla_excel(
        f"Posiciones - {campeonato.nombre}", encabezados, filas,
        logo_path=_logo_reporte(), orientacion="horizontal",
    )
    return enviar_buffer(
        buffer, "campeonatos", f"posiciones-campeonato-{id_campeonato}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/<int:id_campeonato>/posiciones.pdf")
def exportar_posiciones_pdf(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    encabezados, filas = _datos_posiciones_campeonato(campeonato)
    buffer = generar_tabla_pdf(
        f"Tabla de posiciones - {campeonato.nombre}", encabezados, filas,
        orientacion="horizontal", tamano_pagina="carta", tamano_letra=9,
        logo_path=_logo_reporte(),
    )
    return enviar_buffer(
        buffer, "campeonatos", f"posiciones-campeonato-{id_campeonato}.pdf",
        "application/pdf",
    )


@bp.route("/<int:id_campeonato>/jugadores", methods=["GET"])
def jugadores(id_campeonato):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    ids_categoria = [c.id_categoria for c in campeonato.categorias]
    id_categoria = request.args.get("id_categoria", type=int)
    id_equipo = request.args.get("id_equipo", type=int)

    if ids_categoria:
        consulta = Alumno.query.filter(
            Alumno.id_categoria.in_(ids_categoria), Alumno.estado == "Activo"
        )
        if id_categoria and id_categoria in ids_categoria:
            consulta = consulta.filter(Alumno.id_categoria == id_categoria)
        if id_equipo:
            consulta = consulta.filter(Alumno.equipos.any(Equipo.id_equipo == id_equipo))
        candidatos = consulta.order_by(Alumno.apellido, Alumno.nombre).all()
    else:
        candidatos = []

    habilitados = {
        ac.id_alumno: ac.habilitado
        for ac in AlumnoCampeonato.query.filter_by(id_campeonato=id_campeonato).all()
    }
    return render_template(
        "campeonatos/jugadores.html", campeonato=campeonato, candidatos=candidatos,
        habilitados=habilitados, categorias=campeonato.categorias,
        equipos=[equipo for equipo in campeonato.equipos if not equipo.es_rival],
        filtros=request.args,
    )


@bp.route("/<int:id_campeonato>/jugadores/<int:id_alumno>/toggle", methods=["POST"])
def toggle_jugador(id_campeonato, id_alumno):
    campeonato = Campeonato.query.get_or_404(id_campeonato)
    alumno = Alumno.query.get_or_404(id_alumno)
    if campeonato.estado in {"Finalizado", "Cancelado"}:
        flash("La convocatoria está archivada porque el campeonato está cerrado.", "danger")
        return redirect(url_for("campeonatos.jugadores", id_campeonato=id_campeonato))
    if alumno.estado != "Activo":
        flash("No se puede convocar a un alumno retirado.", "danger")
        return redirect(url_for("campeonatos.jugadores", id_campeonato=id_campeonato))
    ids_categoria = {categoria.id_categoria for categoria in campeonato.categorias}
    if alumno.id_categoria not in ids_categoria:
        flash("El alumno no pertenece a una categoría habilitada en este campeonato.", "danger")
        return redirect(url_for("campeonatos.jugadores", id_campeonato=id_campeonato))
    ac = AlumnoCampeonato.query.filter_by(id_campeonato=id_campeonato, id_alumno=id_alumno).first()
    if ac is None:
        ac = AlumnoCampeonato(
            id_campeonato=id_campeonato, id_alumno=id_alumno,
            habilitado=True, archivado=False,
        )
        db.session.add(ac)
    else:
        ac.habilitado = not ac.habilitado
        ac.archivado = False
        ac.archivado_en = None
    db.session.commit()
    return redirect(url_for(
        "campeonatos.jugadores", id_campeonato=id_campeonato,
        id_categoria=request.form.get("id_categoria") or None,
        id_equipo=request.form.get("id_equipo") or None,
    ))


@bp.route("/partidos/<int:id_partido>/resultado", methods=["POST"])
def registrar_resultado(id_partido):
    """Registra el resultado de un partido de campeonato y actualiza la tabla de posiciones."""
    partido = Partido.query.get_or_404(id_partido)
    if partido.id_campeonato is None:
        flash("Este partido no pertenece a un campeonato.", "danger")
        return redirect(url_for("partidos.listar"))
    if partido.campeonato.estado in {"Finalizado", "Cancelado"}:
        flash("Reabra el campeonato antes de corregir resultados.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=partido.id_campeonato))
    fase_posterior_finalizada = Partido.query.filter(
        db.or_(
            Partido.id_partido_origen_local == partido.id_partido,
            Partido.id_partido_origen_visita == partido.id_partido,
        ),
        Partido.estado_partido == "Finalizado",
    ).first()
    if fase_posterior_finalizada:
        flash(
            "No se puede corregir este resultado porque la fase siguiente ya fue "
            "disputada. Reabra primero la fase posterior.",
            "danger",
        )
        return redirect(url_for("campeonatos.detalle", id_campeonato=partido.id_campeonato))
    resultado_anterior = partido.resultado
    penales_anteriores = (
        f"{partido.penales_local}-{partido.penales_visita}"
        if partido.penales_local is not None else None
    )
    try:
        motivo_correccion = texto_opcional(
            request.form.get("motivo_correccion"), "Motivo de corrección", 255
        )
        if resultado_anterior and not motivo_correccion:
            raise ErrorValidacion(
                "Indique el motivo obligatorio para corregir un resultado existente."
            )
        goles_local = entero(
            request.form.get("goles_local"), "Goles del local", 0, 99, requerido=True
        )
        goles_visita = entero(
            request.form.get("goles_visita"), "Goles del visitante", 0, 99, requerido=True
        )
        penales_local = entero(
            request.form.get("penales_local"), "Penales del local", 0, 99
        )
        penales_visita = entero(
            request.form.get("penales_visita"), "Penales del visitante", 0, 99
        )
        if partido.es_eliminatorio and goles_local == goles_visita:
            if penales_local is None or penales_visita is None or penales_local == penales_visita:
                raise ErrorValidacion(
                    "Un partido eliminatorio empatado necesita un ganador por penales."
                )
    except ErrorValidacion as error:
        flash(str(error), "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=partido.id_campeonato))

    partido.goles_local = goles_local
    partido.goles_visita = goles_visita
    partido.penales_local = penales_local
    partido.penales_visita = penales_visita
    partido.resultado = f"{goles_local}-{goles_visita}"
    partido.estado_partido = "Finalizado"
    if partido.campeonato.estado in {"Borrador", "Planificado"}:
        partido.campeonato.estado = "En curso"
    _recalcular_posiciones(partido.id_campeonato)
    _avanzar_eliminatoria(partido)
    db.session.add(Auditoria(
        modulo="Campeonatos",
        accion="Corregir resultado" if resultado_anterior else "Registrar resultado",
        entidad="Partido", id_entidad=partido.id_partido,
        valor_anterior=(f"resultado={resultado_anterior}; penales={penales_anteriores}" if resultado_anterior else None),
        valor_nuevo=f"resultado={partido.resultado}; penales={penales_local}-{penales_visita}" if penales_local is not None else f"resultado={partido.resultado}",
        detalle=(
            f"{resultado_anterior or 'sin resultado'}"
            f"{' penales '+penales_anteriores if penales_anteriores else ''}"
            f" -> {partido.resultado}"
            f"{' penales '+str(penales_local)+'-'+str(penales_visita) if penales_local is not None else ''}; "
            f"motivo={motivo_correccion or 'registro inicial'}"
        ),
    ))
    db.session.commit()
    flash("Resultado registrado y tabla de posiciones actualizada.", "success")
    return redirect(url_for("campeonatos.detalle", id_campeonato=partido.id_campeonato))


@bp.route("/partidos/<int:id_partido>/walkover", methods=["POST"])
def registrar_walkover(id_partido):
    partido = Partido.query.get_or_404(id_partido)
    if not partido.id_campeonato or partido.campeonato.estado in {"Finalizado", "Cancelado"}:
        flash("El partido no admite modificaciones.", "danger")
        return redirect(url_for("campeonatos.listar"))
    ganador = request.form.get("ganador", type=int)
    if ganador not in {partido.id_equipo, partido.id_equipo_rival}:
        flash("Seleccione un ganador válido para el walkover.", "danger")
        return redirect(url_for("campeonatos.detalle", id_campeonato=partido.id_campeonato))
    from app.models import Configuracion
    marcador_wo = Configuracion.obtener().marcador_walkover
    partido.goles_local = marcador_wo if ganador == partido.id_equipo else 0
    partido.goles_visita = marcador_wo if ganador == partido.id_equipo_rival else 0
    partido.resultado = f"{partido.goles_local}-{partido.goles_visita}"
    partido.estado_partido = "Walkover"
    partido.observacion = texto_opcional(
        request.form.get("observacion"), "Motivo del walkover", 255
    ) or "Incomparecencia"
    _recalcular_posiciones(partido.id_campeonato)
    _avanzar_eliminatoria(partido)
    db.session.add(Auditoria(
        modulo="Campeonatos", accion="Walkover", entidad="Partido",
        id_entidad=id_partido, detalle=f"ganador={ganador}; {partido.observacion}",
    ))
    db.session.commit()
    flash("Walkover registrado y tabla actualizada.", "success")
    return redirect(url_for("campeonatos.detalle", id_campeonato=partido.id_campeonato))
