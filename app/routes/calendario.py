import calendar as cal_module
from datetime import date, time, timedelta
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, send_file

from app.extensions import db
from app.models import (EventoAgenda, Campeonato, Entrenamiento, Categoria, Equipo, Lugar, Auditoria,
                        PersonalDeportivo, SesionEntrenamiento, AsistenciaEntrenamiento, Alumno)
from app.utils.validacion import (
    ErrorValidacion, entero, hora_hm, texto_opcional, fecha_iso,
)
from app.utils.calendario_pdf import generar_calendario_pdf
from app.utils.descargas import enviar_buffer
from app.utils.excel import exportar_tabla_excel
from app.utils.pdf_tablas import generar_tabla_pdf
from app.utils.personalizacion import configuracion_y_logo

bp = Blueprint("calendario", __name__, url_prefix="/calendario")

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


@bp.route("/personal", methods=["GET", "POST"])
def personal():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
        else:
            creado = PersonalDeportivo(
                nombre=nombre[:150], documento=request.form.get("documento", "").strip() or None,
                telefono=request.form.get("telefono", "").strip() or None,
                correo=request.form.get("correo", "").strip() or None,
                especialidad=request.form.get("especialidad", "").strip() or None,
                tipo=request.form.get("tipo", "Entrenador")[:20], fecha_ingreso=date.today(),
            )
            db.session.add(creado)
            db.session.flush()
            db.session.add(Auditoria(modulo="Personal", accion="Crear", entidad="PersonalDeportivo", id_entidad=creado.id_personal, valor_nuevo=creado.nombre))
            db.session.commit(); flash("Personal deportivo registrado.", "success")
            return redirect(url_for("calendario.personal"))
    return render_template("calendario/personal.html", personal=PersonalDeportivo.query.order_by(PersonalDeportivo.activo.desc(), PersonalDeportivo.nombre).all())


@bp.route("/personal/<int:id_personal>/estado", methods=["POST"])
def personal_estado(id_personal):
    persona = PersonalDeportivo.query.get_or_404(id_personal)
    persona.activo = not persona.activo
    persona.fecha_salida = None if persona.activo else date.today()
    db.session.add(Auditoria(modulo="Personal", accion="Activar" if persona.activo else "Desactivar", entidad="PersonalDeportivo", id_entidad=persona.id_personal, valor_nuevo=persona.nombre))
    db.session.commit()
    return redirect(url_for("calendario.personal"))


@bp.route("/entrenamientos/<int:id_entrenamiento>/asistencia", methods=["GET", "POST"])
def asistencia(id_entrenamiento):
    entrenamiento = Entrenamiento.query.get_or_404(id_entrenamiento)
    fecha = fecha_iso(request.values.get("fecha") or date.today().isoformat(), "Fecha")
    sesion = SesionEntrenamiento.query.filter_by(id_entrenamiento=id_entrenamiento, fecha=fecha).first()
    consulta = Alumno.query.filter_by(estado="Activo")
    if entrenamiento.id_equipo:
        consulta = consulta.filter(Alumno.equipos.any(Equipo.id_equipo == entrenamiento.id_equipo))
    elif entrenamiento.id_categoria:
        consulta = consulta.filter_by(id_categoria=entrenamiento.id_categoria)
    consulta = consulta.filter(db.or_(Alumno.turno.is_(None), Alumno.turno == entrenamiento.turno))
    alumnos = consulta.order_by(Alumno.apellido, Alumno.nombre).all()
    if request.method == "POST":
        if not sesion:
            sesion = SesionEntrenamiento(entrenamiento=entrenamiento, fecha=fecha)
            db.session.add(sesion); db.session.flush()
        resumen = {"Presente": 0, "Ausente": 0, "Justificado": 0, "Tarde": 0}
        for alumno in alumnos:
            estado = request.form.get(f"estado_{alumno.id_alumno}", "Ausente")
            if estado not in {"Presente", "Ausente", "Justificado", "Tarde"}:
                estado = "Ausente"
            registro = AsistenciaEntrenamiento.query.filter_by(
                id_sesion_entrenamiento=sesion.id_sesion_entrenamiento, id_alumno=alumno.id_alumno
            ).first() or AsistenciaEntrenamiento(sesion=sesion, alumno=alumno)
            registro.estado = estado
            resumen[estado] += 1
            registro.justificacion = request.form.get(f"justificacion_{alumno.id_alumno}", "").strip()[:255] or None
            db.session.add(registro)
        sesion.estado = "Realizada"
        db.session.add(Auditoria(
            modulo="Asistencia", accion="Guardar", entidad="SesionEntrenamiento",
            id_entidad=sesion.id_sesion_entrenamiento,
            valor_nuevo="; ".join(f"{estado}={cantidad}" for estado, cantidad in resumen.items()),
        ))
        db.session.commit(); flash("Asistencia guardada.", "success")
        return redirect(url_for("calendario.asistencia", id_entrenamiento=id_entrenamiento, fecha=fecha.isoformat()))
    registros = {a.id_alumno: a for a in sesion.asistencias} if sesion else {}
    sesion_vista = sesion or SesionEntrenamiento(fecha=fecha)
    return render_template("calendario/asistencia.html", entrenamiento=entrenamiento, sesion=sesion_vista, fecha=fecha,
                           alumnos=alumnos, registros=registros)


@bp.route("/entrenamientos/<int:id_entrenamiento>/asistencia/exportar.<formato>")
def asistencia_exportar(id_entrenamiento, formato):
    if formato not in {"pdf", "xlsx"}:
        return "Formato no válido", 404
    entrenamiento = Entrenamiento.query.get_or_404(id_entrenamiento)
    fecha = fecha_iso(request.args.get("fecha") or date.today().isoformat(), "Fecha")
    sesion = SesionEntrenamiento.query.filter_by(id_entrenamiento=id_entrenamiento, fecha=fecha).first()
    registros = [] if not sesion else sorted(sesion.asistencias, key=lambda r: (r.alumno.apellido, r.alumno.nombre))
    definiciones = [("alumno", "Alumno"), ("estado", "Estado"), ("justificacion", "Justificación")]
    seleccionadas = request.args.getlist("columnas")
    disponibles = {clave: (indice, etiqueta) for indice, (clave, etiqueta) in enumerate(definiciones)}
    if not seleccionadas or any(clave not in disponibles for clave in seleccionadas):
        abort(400, description="Seleccione al menos una columna válida para exportar.")
    valores = [[r.alumno.nombre_completo, r.estado, r.justificacion or "—"] for r in registros]
    indices = [disponibles[clave][0] for clave in seleccionadas]
    encabezados = [disponibles[clave][1] for clave in seleccionadas]
    filas = [[fila[indice] for indice in indices] for fila in valores]
    grupo = entrenamiento.equipo.nombre if entrenamiento.equipo else (entrenamiento.categoria.nombre if entrenamiento.categoria else "General")
    titulo = f"Asistencia {grupo} - {fecha.strftime('%d/%m/%Y')}"
    _, logo = configuracion_y_logo()
    if formato == "pdf":
        archivo = generar_tabla_pdf(titulo, encabezados, filas, logo_path=logo)
        return send_file(archivo, mimetype="application/pdf", as_attachment=True, download_name=f"asistencia_{fecha.isoformat()}.pdf")
    archivo = exportar_tabla_excel(titulo, encabezados, filas, logo_path=logo)
    return send_file(archivo, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=f"asistencia_{fecha.isoformat()}.xlsx")


@bp.route("/entrenamientos/<int:id_entrenamiento>/asistencia/exportar")
def asistencia_exportar_form(id_entrenamiento):
    entrenamiento = Entrenamiento.query.get_or_404(id_entrenamiento)
    fecha = fecha_iso(request.args.get("fecha") or date.today().isoformat(), "Fecha")
    return render_template("calendario/asistencia_exportar.html", entrenamiento=entrenamiento, fecha=fecha)


def _items_exportacion(inicio, fin, id_categoria=None, id_equipo=None):
    consulta_eventos = EventoAgenda.query.filter(EventoAgenda.fecha.between(inicio, fin))
    consulta_entrenamientos = Entrenamiento.query.filter_by(activo=True)
    if id_categoria:
        consulta_eventos = consulta_eventos.filter_by(id_categoria=id_categoria)
        consulta_entrenamientos = consulta_entrenamientos.filter_by(id_categoria=id_categoria)
    if id_equipo:
        consulta_eventos = consulta_eventos.filter_by(id_equipo=id_equipo)
        consulta_entrenamientos = consulta_entrenamientos.filter_by(id_equipo=id_equipo)

    items = [{
        "fecha": evento.fecha,
        "tipo": evento.tipo,
        "texto": evento.descripcion,
        "hora": evento.hora,
        "lugar": evento.lugar or (evento.partido.cancha if evento.partido else None),
        "categoria": evento.categoria.nombre if evento.categoria else None,
        "equipo": evento.equipo.nombre if evento.equipo else None,
    } for evento in consulta_eventos.all()]

    consulta_campeonatos = Campeonato.query.filter(
        Campeonato.fecha_inicio <= fin,
        db.or_(Campeonato.fecha_fin.is_(None), Campeonato.fecha_fin >= inicio),
    )
    for campeonato in consulta_campeonatos.all():
        if id_categoria and not any(c.id_categoria == id_categoria for c in campeonato.categorias):
            continue
        if id_equipo and not any(e.id_equipo == id_equipo for e in campeonato.equipos):
            continue
        fecha = max(campeonato.fecha_inicio, inicio)
        fecha_final = min(campeonato.fecha_fin or fin, fin)
        while fecha <= fecha_final:
            items.append({
                "fecha": fecha, "tipo": "Campeonato", "texto": campeonato.nombre,
                "hora": None, "lugar": campeonato.lugar,
                "categoria": ", ".join(c.nombre for c in campeonato.categorias) or None,
                "equipo": ", ".join(e.nombre for e in campeonato.equipos) or None,
            })
            fecha += timedelta(days=1)

    for entrenamiento in consulta_entrenamientos.all():
        fecha = inicio
        while fecha <= fin:
            if (
                fecha.weekday() == entrenamiento.dia_semana
                and (not entrenamiento.fecha_inicio or fecha >= entrenamiento.fecha_inicio)
                and (not entrenamiento.fecha_fin or fecha <= entrenamiento.fecha_fin)
            ):
                etiqueta = entrenamiento.equipo.nombre if entrenamiento.equipo else (
                    entrenamiento.categoria.nombre if entrenamiento.categoria else "General"
                )
                items.append({
                    "fecha": fecha, "tipo": "Entrenamiento",
                    "texto": f"Entrenamiento - {etiqueta}",
                    "hora": entrenamiento.hora_inicio, "lugar": entrenamiento.lugar,
                    "categoria": entrenamiento.categoria.nombre if entrenamiento.categoria else None,
                    "equipo": entrenamiento.equipo.nombre if entrenamiento.equipo else None,
                })
            fecha += timedelta(days=1)
    return sorted(items, key=lambda item: (
        item["fecha"], item["hora"] is None, item["hora"] or time.max, item["texto"]
    ))


@bp.route("/")
def ver():
    hoy = date.today()
    anio = request.args.get("anio", type=int, default=hoy.year)
    mes = request.args.get("mes", type=int, default=hoy.month)
    if not 1 <= mes <= 12 or not 2000 <= anio <= 2100:
        flash("El mes o año solicitado no es válido.", "warning")
        return redirect(url_for("calendario.ver", anio=hoy.year, mes=hoy.month))

    primer_dia_semana, dias_en_mes = cal_module.monthrange(anio, mes)
    inicio_mes = date(anio, mes, 1)
    fin_mes = date(anio, mes, dias_en_mes)

    id_categoria_filtro = request.args.get("id_categoria", type=int)
    id_equipo_filtro = request.args.get("id_equipo", type=int)
    consulta_eventos = EventoAgenda.query.filter(
        EventoAgenda.fecha >= inicio_mes, EventoAgenda.fecha <= fin_mes
    )
    consulta_entrenamientos = Entrenamiento.query.filter_by(activo=True)
    if id_categoria_filtro:
        consulta_eventos = consulta_eventos.filter_by(id_categoria=id_categoria_filtro)
        consulta_entrenamientos = consulta_entrenamientos.filter_by(id_categoria=id_categoria_filtro)
    if id_equipo_filtro:
        consulta_eventos = consulta_eventos.filter_by(id_equipo=id_equipo_filtro)
        consulta_entrenamientos = consulta_entrenamientos.filter_by(id_equipo=id_equipo_filtro)
    eventos = consulta_eventos.all()
    campeonatos = Campeonato.query.filter(
        Campeonato.fecha_inicio <= fin_mes,
        db.or_(Campeonato.fecha_fin.is_(None), Campeonato.fecha_fin >= inicio_mes),
    ).all()
    if id_categoria_filtro:
        campeonatos = [
            campeonato for campeonato in campeonatos
            if any(categoria.id_categoria == id_categoria_filtro for categoria in campeonato.categorias)
        ]
    if id_equipo_filtro:
        campeonatos = [
            campeonato for campeonato in campeonatos
            if any(equipo.id_equipo == id_equipo_filtro for equipo in campeonato.equipos)
        ]
    entrenamientos = consulta_entrenamientos.all()

    # Arma un diccionario {dia: [items]}
    dias = {d: [] for d in range(1, dias_en_mes + 1)}
    for ev in eventos:
        dias[ev.fecha.day].append({
            "tipo": ev.tipo,
            "texto": ev.descripcion,
            "hora": ev.hora,
            "hora_fin": None,
            "lugar": ev.lugar or (ev.partido.cancha if ev.partido else None),
            "maps_url": (
                ev.lugar_catalogo.google_maps_url
                if ev.lugar_catalogo else (
                    ev.partido.lugar_catalogo.google_maps_url
                    if ev.partido and ev.partido.lugar_catalogo else None
                )
            ),
            "categoria": ev.categoria.nombre if ev.categoria else None,
            "equipo": ev.equipo.nombre if ev.equipo else None,
        })
    for c in campeonatos:
        ini = max(c.fecha_inicio, inicio_mes)
        fin = min(c.fecha_fin or fin_mes, fin_mes)
        d = ini
        while d <= fin:
            dias[d.day].append({
                "tipo": "Campeonato", "texto": c.nombre, "hora": None,
                "hora_fin": None, "lugar": c.lugar,
                "maps_url": c.lugar_catalogo.google_maps_url if c.lugar_catalogo else None,
                "categoria": ", ".join(cat.nombre for cat in c.categorias) or None,
                "equipo": ", ".join(eq.nombre for eq in c.equipos) or None,
            })
            d = d.fromordinal(d.toordinal() + 1)
    for e in entrenamientos:
        for d in range(1, dias_en_mes + 1):
            fecha = date(anio, mes, d)
            if e.fecha_inicio and fecha < e.fecha_inicio:
                continue
            if e.fecha_fin and fecha > e.fecha_fin:
                continue
            if fecha.weekday() == e.dia_semana:
                etiqueta = e.equipo.nombre if e.equipo else (e.categoria.nombre if e.categoria else "General")
                dias[d].append({
                    "tipo": "Entrenamiento",
                    "texto": f"Entrenamiento - {etiqueta}",
                    "hora": e.hora_inicio,
                    "hora_fin": e.hora_fin,
                    "lugar": e.lugar,
                    "maps_url": e.lugar_catalogo.google_maps_url if e.lugar_catalogo else None,
                    "categoria": e.categoria.nombre if e.categoria else None,
                    "equipo": e.equipo.nombre if e.equipo else None,
                })

    for items in dias.values():
        items.sort(key=lambda item: (item["hora"] is None, item["hora"] or time.max, item["texto"]))

    actividades_mes = []
    resumen_tipos = {"Evento": 0, "Partido": 0, "Entrenamiento": 0, "Campeonato": 0}
    for numero_dia, items in dias.items():
        fecha_actividad = date(anio, mes, numero_dia)
        for item in items:
            actividad = dict(item)
            actividad["fecha"] = fecha_actividad
            actividad["nombre_dia"] = DIAS_SEMANA[fecha_actividad.weekday()]
            actividades_mes.append(actividad)
            resumen_tipos[item["tipo"]] = resumen_tipos.get(item["tipo"], 0) + 1
    agenda_desde_hoy = (anio, mes) == (hoy.year, hoy.month)
    actividades_vista = (
        [actividad for actividad in actividades_mes if actividad["fecha"] >= hoy]
        if agenda_desde_hoy else actividades_mes
    )

    semanas = []
    semana = [None] * primer_dia_semana
    for d in range(1, dias_en_mes + 1):
        semana.append(d)
        if len(semana) == 7:
            semanas.append(semana)
            semana = []
    if semana:
        semana += [None] * (7 - len(semana))
        semanas.append(semana)

    mes_anterior = mes - 1 if mes > 1 else 12
    anio_mes_anterior = anio if mes > 1 else anio - 1
    mes_siguiente = mes + 1 if mes < 12 else 1
    anio_mes_siguiente = anio if mes < 12 else anio + 1

    return render_template(
        "calendario/ver.html",
        anio=anio, mes=mes, semanas=semanas, dias=dias,
        nombre_mes=MESES_ES[mes - 1],
        actividades_mes=actividades_mes, actividades_vista=actividades_vista,
        agenda_desde_hoy=agenda_desde_hoy, resumen_tipos=resumen_tipos,
        total_actividades=len(actividades_mes),
        dias_con_actividad=sum(1 for items in dias.values() if items),
        hoy=hoy,
        mes_anterior=mes_anterior, anio_mes_anterior=anio_mes_anterior,
        mes_siguiente=mes_siguiente, anio_mes_siguiente=anio_mes_siguiente,
        categorias=Categoria.query.order_by(Categoria.nombre).all(),
        equipos=Equipo.query.filter_by(es_rival=False, activo=True).order_by(Equipo.nombre).all(),
        filtros=request.args,
        fecha_semana=(hoy if (anio, mes) == (hoy.year, hoy.month) else inicio_mes),
    )


@bp.route("/exportar-mensual.pdf")
def exportar_mensual_pdf():
    hoy = date.today()
    anio = request.args.get("anio", type=int, default=hoy.year)
    mes = request.args.get("mes", type=int, default=hoy.month)
    if not 1 <= mes <= 12 or not 2000 <= anio <= 2100:
        flash("El mes o año solicitado no es válido.", "warning")
        return redirect(url_for("calendario.ver"))
    inicio = date(anio, mes, 1)
    fin = date(anio, mes, cal_module.monthrange(anio, mes)[1])
    items = _items_exportacion(
        inicio, fin,
        request.args.get("id_categoria", type=int),
        request.args.get("id_equipo", type=int),
    )
    buffer = generar_calendario_pdf(
        f"Calendario mensual - {MESES_ES[mes - 1]} {anio}",
        inicio, fin, items, vista="mensual",
    )
    return enviar_buffer(
        buffer, "calendarios", f"calendario-mensual-{anio}-{mes:02d}.pdf",
        "application/pdf",
    )


@bp.route("/exportar-semanal.pdf")
def exportar_semanal_pdf():
    hoy = date.today()
    try:
        fecha_referencia = fecha_iso(
            request.args.get("fecha") or hoy.isoformat(), "Fecha de la semana"
        )
    except ErrorValidacion as error:
        flash(str(error), "warning")
        return redirect(url_for("calendario.ver"))
    inicio = fecha_referencia - timedelta(days=fecha_referencia.weekday())
    fin = inicio + timedelta(days=6)
    items = _items_exportacion(
        inicio, fin,
        request.args.get("id_categoria", type=int),
        request.args.get("id_equipo", type=int),
    )
    buffer = generar_calendario_pdf(
        f"Calendario semanal - {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')}",
        inicio, fin, items, vista="semanal",
    )
    return enviar_buffer(
        buffer, "calendarios", f"calendario-semanal-{inicio.isoformat()}.pdf",
        "application/pdf",
    )


@bp.route("/entrenamientos")
def listar_entrenamientos():
    entrenamientos = Entrenamiento.query.order_by(Entrenamiento.dia_semana).all()
    return render_template("calendario/entrenamientos.html", entrenamientos=entrenamientos, dias_semana=DIAS_SEMANA)


@bp.route("/entrenamientos/nuevo", methods=["GET", "POST"])
def crear_entrenamiento():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()
    entrenadores = PersonalDeportivo.query.filter_by(activo=True).order_by(PersonalDeportivo.nombre).all()

    if request.method == "POST":
        try:
            dia_semana = entero(
                request.form.get("dia_semana"), "Día de la semana", 0, 6, requerido=True
            )
            hora_inicio = hora_hm(request.form.get("hora_inicio"), "Hora de inicio", True)
            hora_fin = hora_hm(request.form.get("hora_fin"), "Hora de fin")
            if hora_fin and hora_fin <= hora_inicio:
                raise ErrorValidacion("La hora de fin debe ser posterior a la hora de inicio.")
            fecha_inicio = fecha_iso(
                request.form.get("fecha_inicio"), "Fecha de inicio", requerida=False
            )
            fecha_fin = fecha_iso(
                request.form.get("fecha_fin"), "Fecha de fin", requerida=False
            )
            if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
                raise ErrorValidacion("La fecha final no puede ser anterior al inicio.")
            id_categoria = request.form.get("id_categoria", type=int) or None
            id_equipo = request.form.get("id_equipo", type=int) or None
            id_entrenador = request.form.get("id_entrenador", type=int) or None
            if id_entrenador and not db.session.get(PersonalDeportivo, id_entrenador):
                raise ErrorValidacion("El entrenador seleccionado no existe.")
            if id_categoria and db.session.get(Categoria, id_categoria) is None:
                raise ErrorValidacion("La categoría seleccionada no existe.")
            equipo = db.session.get(Equipo, id_equipo) if id_equipo else None
            if id_equipo and (equipo is None or equipo.es_rival or not equipo.activo):
                raise ErrorValidacion("El equipo seleccionado no existe o está inactivo.")
            nombre_lugar = texto_opcional(request.form.get("lugar"), "Lugar", 150)
            lugar_catalogo = Lugar.query.filter(
                db.func.lower(Lugar.nombre) == nombre_lugar.lower()
            ).first() if nombre_lugar else None
            if nombre_lugar:
                conflictos = Entrenamiento.query.filter_by(
                    dia_semana=dia_semana, activo=True
                )
                if lugar_catalogo:
                    conflictos = conflictos.filter_by(id_lugar=lugar_catalogo.id_lugar)
                else:
                    conflictos = conflictos.filter(
                        db.func.lower(Entrenamiento.lugar) == nombre_lugar.lower()
                    )
                for otro in conflictos.all():
                    otro_fin = otro.hora_fin or otro.hora_inicio
                    fin_actual = hora_fin or hora_inicio
                    if hora_inicio < otro_fin and fin_actual > otro.hora_inicio:
                        raise ErrorValidacion("Existe otro entrenamiento en ese lugar y horario.")
            if id_entrenador:
                for otro in Entrenamiento.query.filter_by(dia_semana=dia_semana, id_entrenador=id_entrenador, activo=True).all():
                    if hora_inicio < (otro.hora_fin or otro.hora_inicio) and (hora_fin or hora_inicio) > otro.hora_inicio:
                        raise ErrorValidacion("El entrenador ya tiene otro entrenamiento en ese horario.")
            entrenamiento = Entrenamiento(
            dia_semana=dia_semana,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            lugar=nombre_lugar,
            id_lugar=lugar_catalogo.id_lugar if lugar_catalogo else None,
            fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
            id_categoria=id_categoria, id_equipo=id_equipo,
            id_entrenador=id_entrenador,
            )
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "calendario/entrenamiento_form.html",
                categorias=categorias, equipos=equipos, lugares=lugares, entrenadores=entrenadores,
                dias_semana=DIAS_SEMANA,
            )
        db.session.add(entrenamiento)
        db.session.flush()
        db.session.add(Auditoria(
            modulo="Calendario", accion="Crear entrenamiento",
            entidad="Entrenamiento", id_entidad=entrenamiento.id_entrenamiento,
            detalle=f"día={entrenamiento.dia_semana}; {entrenamiento.hora_inicio}",
        ))
        db.session.commit()
        flash("Entrenamiento fijo agregado al calendario.", "success")
        return redirect(url_for("calendario.listar_entrenamientos"))

    return render_template(
        "calendario/entrenamiento_form.html", categorias=categorias,
        equipos=equipos, lugares=lugares, entrenadores=entrenadores, dias_semana=DIAS_SEMANA,
    )


@bp.route("/entrenamientos/<int:id_entrenamiento>/eliminar", methods=["POST"])
def eliminar_entrenamiento(id_entrenamiento):
    e = Entrenamiento.query.get_or_404(id_entrenamiento)
    db.session.add(Auditoria(
        modulo="Calendario", accion="Eliminar entrenamiento",
        entidad="Entrenamiento", id_entidad=e.id_entrenamiento,
        detalle=f"día={e.dia_semana}; {e.hora_inicio}",
    ))
    db.session.delete(e)
    db.session.commit()
    flash("Entrenamiento eliminado.", "success")
    return redirect(url_for("calendario.listar_entrenamientos"))


@bp.route("/entrenamientos/<int:id_entrenamiento>/editar", methods=["GET", "POST"])
def editar_entrenamiento(id_entrenamiento):
    entrenamiento = Entrenamiento.query.get_or_404(id_entrenamiento)
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = Equipo.query.filter_by(es_rival=False, activo=True).order_by(Equipo.nombre).all()
    lugares = Lugar.query.filter_by(activo=True).order_by(Lugar.nombre).all()
    entrenadores = PersonalDeportivo.query.filter_by(activo=True).order_by(PersonalDeportivo.nombre).all()
    if request.method == "POST":
        try:
            dia_semana = entero(
                request.form.get("dia_semana"), "Día", 0, 6, requerido=True
            )
            hora_inicio = hora_hm(request.form.get("hora_inicio"), "Hora de inicio", True)
            hora_fin = hora_hm(request.form.get("hora_fin"), "Hora de fin")
            if hora_fin and hora_fin <= hora_inicio:
                raise ErrorValidacion("La hora de fin debe ser posterior al inicio.")
            fecha_inicio = fecha_iso(request.form.get("fecha_inicio"), "Inicio", requerida=False)
            fecha_fin = fecha_iso(request.form.get("fecha_fin"), "Fin", requerida=False)
            if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
                raise ErrorValidacion("La fecha final no puede ser anterior al inicio.")
            id_categoria = request.form.get("id_categoria", type=int) or None
            id_equipo = request.form.get("id_equipo", type=int) or None
            id_entrenador = request.form.get("id_entrenador", type=int) or None
            if id_entrenador and not db.session.get(PersonalDeportivo, id_entrenador):
                raise ErrorValidacion("El entrenador seleccionado no existe.")
            if id_categoria and db.session.get(Categoria, id_categoria) is None:
                raise ErrorValidacion("La categoría no existe.")
            equipo = db.session.get(Equipo, id_equipo) if id_equipo else None
            if id_equipo and (equipo is None or equipo.es_rival or not equipo.activo):
                raise ErrorValidacion("El equipo no existe o está inactivo.")
            nombre_lugar = texto_opcional(request.form.get("lugar"), "Lugar", 150)
            lugar = Lugar.query.filter(
                db.func.lower(Lugar.nombre) == nombre_lugar.lower()
            ).first() if nombre_lugar else None
            conflictos = Entrenamiento.query.filter(
                Entrenamiento.id_entrenamiento != id_entrenamiento,
                Entrenamiento.dia_semana == dia_semana,
                Entrenamiento.activo.is_(True),
            )
            if lugar:
                conflictos = conflictos.filter_by(id_lugar=lugar.id_lugar)
            for otro in conflictos.all():
                if hora_inicio < (otro.hora_fin or otro.hora_inicio) and (hora_fin or hora_inicio) > otro.hora_inicio:
                    raise ErrorValidacion("Existe otro entrenamiento en ese lugar y horario.")
            if id_entrenador:
                ocupados = Entrenamiento.query.filter(
                    Entrenamiento.id_entrenamiento != id_entrenamiento,
                    Entrenamiento.dia_semana == dia_semana,
                    Entrenamiento.id_entrenador == id_entrenador,
                    Entrenamiento.activo.is_(True),
                ).all()
                if any(hora_inicio < (o.hora_fin or o.hora_inicio) and (hora_fin or hora_inicio) > o.hora_inicio for o in ocupados):
                    raise ErrorValidacion("El entrenador ya tiene otro entrenamiento en ese horario.")
            entrenamiento.dia_semana = dia_semana
            entrenamiento.hora_inicio = hora_inicio
            entrenamiento.hora_fin = hora_fin
            entrenamiento.fecha_inicio = fecha_inicio
            entrenamiento.fecha_fin = fecha_fin
            entrenamiento.id_categoria = id_categoria
            entrenamiento.id_equipo = id_equipo
            entrenamiento.id_entrenador = id_entrenador
            entrenamiento.lugar = nombre_lugar
            entrenamiento.id_lugar = lugar.id_lugar if lugar else None
        except ErrorValidacion as error:
            flash(str(error), "danger")
        else:
            db.session.add(Auditoria(
                modulo="Calendario", accion="Editar entrenamiento",
                entidad="Entrenamiento", id_entidad=id_entrenamiento,
                detalle=f"día={dia_semana}; {hora_inicio}",
            ))
            db.session.commit()
            flash("Entrenamiento actualizado.", "success")
            return redirect(url_for("calendario.listar_entrenamientos"))
    return render_template(
        "calendario/entrenamiento_form.html", entrenamiento=entrenamiento,
        categorias=categorias, equipos=equipos, lugares=lugares, entrenadores=entrenadores,
        dias_semana=DIAS_SEMANA,
    )
