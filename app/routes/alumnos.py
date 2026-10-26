import os
import uuid
from urllib.parse import urlencode
from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    current_app, flash, abort, send_file, g
)
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps, UnidentifiedImageError
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models import (
    Alumno, Categoria, Equipo, Campeonato, AlumnoCampeonato,
    Configuracion,
    ESTADOS_ALUMNO, POSICIONES, PIERNAS, SEXOS, BECAS, TURNOS, ESTADOS_MENSUALIDAD,
    HistorialAlumno, Auditoria, alumno_equipo, InscripcionGestion,
    HistorialCategoriaAlumno, HistorialEquipoAlumno, BecaHistorial, Tarifa,
    Tutor, AlumnoTutor, Entrenamiento, SesionEntrenamiento, AsistenciaEntrenamiento,
)
from app.utils.reglas import categoria_automatica_por_edad
from app.utils.pdf_tablas import generar_tabla_pdf
from app.utils.excel import exportar_tabla_excel
from app.utils.ficha_alumno_pdf import generar_ficha_alumno
from app.utils.personalizacion import configuracion_y_logo
from app.utils.descargas import enviar_buffer
from app.utils.autorizacion import tiene_permiso
from app.utils.validacion import (
    ErrorValidacion, decimal_positivo, fecha_iso, fecha_no_futura,
    opcion, texto_opcional, texto_requerido, solo_numeros_opcional,
)


bp = Blueprint("alumnos", __name__, url_prefix="/alumnos")


def _usuario_actual_id():
    usuario = getattr(g, "usuario_actual", None)
    return usuario.id_usuario if usuario else None


def _crear_ciclo_inicial(alumno, equipos, motivo="Registro inicial"):
    hoy = date.today()
    config = Configuracion.obtener()
    tarifa = Tarifa.query.filter_by(concepto="Mensualidad", activo=True).order_by(Tarifa.fecha_inicio.desc()).first()
    porcentaje = {"Ninguna": 0, "Media": 50, "Completa": 100}.get(alumno.beca, 0)
    db.session.add(InscripcionGestion(
        id_alumno=alumno.id_alumno, gestion=config.gestion_ficha, fecha_inscripcion=hoy,
        estado="Activa" if alumno.estado == "Activo" else "Retirada",
        id_categoria=alumno.id_categoria, id_equipo_principal=equipos[0].id_equipo if equipos else None,
        id_tarifa=tarifa.id_tarifa if tarifa else None, porcentaje_beca=porcentaje, observacion=motivo,
    ))
    if alumno.id_categoria:
        db.session.add(HistorialCategoriaAlumno(
            id_alumno=alumno.id_alumno, id_categoria=alumno.id_categoria, fecha_inicio=hoy,
            tipo_asignacion="Manual" if alumno.categoria_manual else "Automática",
            motivo=motivo, id_usuario=_usuario_actual_id(),
        ))
    for indice, equipo in enumerate(equipos):
        db.session.add(HistorialEquipoAlumno(
            id_alumno=alumno.id_alumno, id_equipo=equipo.id_equipo, gestion=config.gestion_ficha,
            fecha_inicio=hoy, principal=indice == 0, id_usuario=_usuario_actual_id(),
        ))
    if porcentaje:
        db.session.add(BecaHistorial(
            id_alumno=alumno.id_alumno, porcentaje=porcentaje, fecha_inicio=hoy,
            fecha_fin=alumno.beca_fecha_fin, motivo=motivo, estado="Activa",
            id_usuario=_usuario_actual_id(),
        ))


def _sincronizar_tutores(alumno):
    nombres = [(alumno.tutor, True), (alumno.tutor2, False)]
    vigentes = []
    for nombre, principal in nombres:
        if not nombre:
            continue
        tutor = Tutor.query.filter(db.func.lower(Tutor.nombre) == nombre.strip().lower()).first()
        if not tutor:
            tutor = Tutor(nombre=nombre.strip())
            db.session.add(tutor); db.session.flush()
        relacion = AlumnoTutor.query.filter_by(id_alumno=alumno.id_alumno, id_tutor=tutor.id_tutor).first()
        if not relacion:
            relacion = AlumnoTutor(alumno=alumno, tutor=tutor)
            db.session.add(relacion)
        relacion.principal = principal
        vigentes.append(tutor.id_tutor)
    AlumnoTutor.query.filter(
        AlumnoTutor.id_alumno == alumno.id_alumno,
        AlumnoTutor.id_tutor.notin_(vigentes or [-1]),
    ).delete(synchronize_session=False)

COLUMNAS_EXPORTACION = {
    "alumno": ("Alumno", lambda a: a.nombre_completo),
    "ci": ("CI", lambda a: a.ci or "-"),
    "categoria": ("Categoría", lambda a: a.categoria.nombre if a.categoria else "-"),
    "edad": ("Edad", lambda a: a.edad),
    "equipos": ("Equipos", lambda a: ", ".join(e.nombre for e in a.equipos) or "-"),
    "posicion": ("Posición", lambda a: a.posicion or "-"),
    "turno": ("Turno", lambda a: a.turno or "-"),
    "beca": ("Beca", lambda a: a.beca),
    "sexo": ("Sexo", lambda a: a.sexo or "-"),
    "campeonatos": ("Campeonatos activos", lambda a: ", ".join(a.campeonatos_activos) or "-"),
    "mensualidad": ("Estado mensualidad", lambda a: a.estado_mensualidad),
    "estado": ("Estado alumno", lambda a: a.estado),
    "telefono": ("Teléfono", lambda a: a.telefono or "-"),
}


def _datos_alumno_formulario(id_alumno=None):
    fecha_nacimiento = fecha_no_futura(
        fecha_iso(request.form.get("fecha_nacimiento"), "Fecha de nacimiento"),
        "Fecha de nacimiento",
    )
    ci = solo_numeros_opcional(request.form.get("ci"), "CI", 30)
    if ci:
        duplicado = Alumno.query.filter(db.func.lower(Alumno.ci) == ci.lower())
        if id_alumno:
            duplicado = duplicado.filter(Alumno.id_alumno != id_alumno)
        if duplicado.first():
            raise ErrorValidacion("Ya existe un alumno con ese CI.")

    id_categoria = request.form.get("id_categoria", type=int)
    if id_categoria and db.session.get(Categoria, id_categoria) is None:
        raise ErrorValidacion("La categoría seleccionada no existe.")

    ids_equipos = []
    for valor in request.form.getlist("equipos"):
        try:
            ids_equipos.append(int(valor))
        except (TypeError, ValueError):
            raise ErrorValidacion("Uno de los equipos seleccionados no es válido.")
    equipos = Equipo.query.filter(
        Equipo.id_equipo.in_(ids_equipos),
        Equipo.es_rival.is_(False),
    ).all() if ids_equipos else []
    if len(equipos) != len(set(ids_equipos)):
        raise ErrorValidacion("Uno de los equipos seleccionados no existe.")

    beca = opcion(request.form.get("beca", "Ninguna"), BECAS, "Beca")
    beca_fecha_fin = fecha_iso(request.form.get("beca_fecha_fin"), "Vigencia de beca", requerida=False)
    if beca == "Ninguna":
        beca_fecha_fin = None

    datos = {
        "nombre": texto_requerido(request.form.get("nombre"), "Nombre", 80),
        "apellido": texto_requerido(request.form.get("apellido"), "Apellido", 80),
        "fecha_nacimiento": fecha_nacimiento,
        "ci": ci,
        "direccion": texto_opcional(request.form.get("direccion"), "Dirección", 255),
        "tutor": texto_opcional(request.form.get("tutor"), "Tutor", 120),
        "tutor2": texto_opcional(request.form.get("tutor2"), "Tutor 2", 120),
        "telefono": solo_numeros_opcional(request.form.get("telefono"), "Teléfono", 30),
        "estado": opcion(request.form.get("estado", "Activo"), ESTADOS_ALUMNO, "Estado"),
        "posicion": opcion(request.form.get("posicion"), POSICIONES, "Posición", opcional=True),
        "turno": opcion(request.form.get("turno"), TURNOS, "Turno", opcional=True),
        "pierna_habil": opcion(request.form.get("pierna_habil"), PIERNAS, "Pierna hábil", opcional=True),
        "peso": decimal_positivo(request.form.get("peso"), "Peso", 500),
        "estatura": decimal_positivo(request.form.get("estatura"), "Estatura", 3),
        "sexo": opcion(request.form.get("sexo"), SEXOS, "Sexo", opcional=True),
        "beca": beca,
        "beca_fecha_fin": beca_fecha_fin,
    }
    return datos, id_categoria, equipos


def _datos_exportacion_alumnos(alumnos):
    solicitadas = request.args.getlist("columnas")
    # Compatibilidad con formularios que el navegador pudiera conservar en
    # caché antes de unificar nombre y apellido en una sola columna.
    if "nombre" in solicitadas or "apellido" in solicitadas:
        solicitadas = ["alumno" if clave in {"nombre", "apellido"} else clave for clave in solicitadas]
    solicitadas = list(dict.fromkeys(solicitadas))
    claves = [clave for clave in solicitadas if clave in COLUMNAS_EXPORTACION]
    if not claves:
        abort(400, description="Debe seleccionar al menos una columna para exportar.")
    encabezados = ["N°"] + [COLUMNAS_EXPORTACION[clave][0] for clave in claves]
    filas = [
        [numero] + [COLUMNAS_EXPORTACION[clave][1](alumno) for clave in claves]
        for numero, alumno in enumerate(alumnos, start=1)
    ]
    return encabezados, filas


def _nombre_exportacion(predeterminado):
    solicitado = request.args.get("nombre_archivo", "").strip()
    titulo = solicitado[:100] if solicitado else predeterminado
    nombre_seguro = secure_filename(titulo).rsplit(".", 1)[0] or secure_filename(predeterminado)
    return titulo, nombre_seguro


def _extensión_permitida(nombre_archivo):
    return (
        "." in nombre_archivo
        and nombre_archivo.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_PHOTO_EXT"]
    )


def _guardar_foto(archivo):
    if not archivo or archivo.filename == "":
        return None
    if not _extensión_permitida(archivo.filename):
        flash("Formato de imagen no permitido (use png, jpg, jpeg o webp).", "warning")
        return None
    ext = archivo.filename.rsplit(".", 1)[1].lower()
    try:
        imagen = Image.open(archivo.stream)
        imagen.verify()
        archivo.stream.seek(0)
        imagen = ImageOps.exif_transpose(Image.open(archivo.stream))
        imagen.thumbnail((1600, 1600))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        flash("El archivo no contiene una imagen válida.", "warning")
        return None
    formato = (imagen.format or ext).upper()
    extensiones = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
    if formato not in extensiones:
        flash("El contenido de la imagen no corresponde a un formato permitido.", "warning")
        return None
    ext = extensiones[formato]
    nombre_unico = f"{uuid.uuid4().hex}.{ext}"
    ruta = os.path.join(current_app.config["UPLOAD_FOLDER"], nombre_unico)
    if formato == "JPEG" and imagen.mode not in ("RGB", "L"):
        imagen = imagen.convert("RGB")
    imagen.save(ruta, formato, optimize=True, quality=88)
    return nombre_unico


def _eliminar_foto(nombre):
    if not nombre:
        return
    ruta = os.path.join(current_app.config["UPLOAD_FOLDER"], nombre)
    if os.path.isfile(ruta):
        os.remove(ruta)


def _filtrar_alumnos(args, paginar=False):
    """Aplica todos los filtros del módulo de alumnos y devuelve la lista
    resultante ya ordenada."""
    nombre = args.get("nombre", "").strip()
    apellido = args.get("apellido", "").strip()
    id_categoria = args.get("id_categoria", type=int)
    edad = args.get("edad", type=int)
    posicion = args.get("posicion", "")
    beca = args.get("beca", "")
    sexo = args.get("sexo", "")
    turno = args.get("turno", "")
    id_campeonato = args.get("id_campeonato", type=int)
    estado_mensualidad = args.get("estado_mensualidad", "")
    id_equipo = args.get("id_equipo", type=int)
    estado = args.get("estado", "Activo")
    orden = args.get("orden", "alfabetico")
    id_interno = args.get("id_alumno", type=int)

    query = Alumno.query.options(
        joinedload(Alumno.categoria),
        selectinload(Alumno.equipos),
        selectinload(Alumno.pagos),
        selectinload(Alumno.campeonatos_habilitados).joinedload(AlumnoCampeonato.campeonato),
    )
    if id_interno:
        query = query.filter(Alumno.id_alumno == id_interno)
    if nombre:
        query = query.filter(Alumno.nombre.ilike(f"%{nombre}%"))
    if apellido:
        query = query.filter(Alumno.apellido.ilike(f"%{apellido}%"))
    if id_categoria:
        query = query.filter(Alumno.id_categoria == id_categoria)
    if posicion:
        query = query.filter(Alumno.posicion == posicion)
    if beca:
        query = query.filter(Alumno.beca == beca)
    if sexo:
        query = query.filter(Alumno.sexo == sexo)
    if turno:
        query = query.filter(Alumno.turno == turno)
    if estado:
        query = query.filter(Alumno.estado == estado)
    if id_equipo:
        query = query.filter(Alumno.equipos.any(Equipo.id_equipo == id_equipo))
    if id_campeonato:
        query = query.filter(
            Alumno.campeonatos_habilitados.any(
                db.and_(AlumnoCampeonato.id_campeonato == id_campeonato, AlumnoCampeonato.habilitado.is_(True))
            )
        )
    if edad is not None and edad >= 0:
        hoy = date.today()
        nacimiento_maximo = hoy - relativedelta(years=edad)
        nacimiento_minimo = hoy - relativedelta(years=edad + 1) + timedelta(days=1)
        query = query.filter(
            Alumno.fecha_nacimiento.between(nacimiento_minimo, nacimiento_maximo)
        )

    if orden == "categoria":
        query = query.outerjoin(Categoria, Alumno.id_categoria == Categoria.id_categoria)
        query = query.order_by(Categoria.edad_min.asc().nullslast(), Alumno.apellido, Alumno.nombre)
    else:
        query = query.order_by(Alumno.apellido, Alumno.nombre)

    if paginar and not estado_mensualidad:
        pagina = max(args.get("page", 1, type=int), 1)
        paginacion = query.paginate(
            page=pagina,
            per_page=current_app.config.get("ITEMS_PER_PAGE", 40),
            error_out=False,
        )
        return paginacion.items, paginacion

    alumnos = query.all()
    if estado_mensualidad:
        if estado_mensualidad == "Con deuda":
            alumnos = [
                a for a in alumnos
                if a.estado == "Activo"
                and a.estado_mensualidad in {"Vencido", "Sin pagos"}
            ]
        else:
            alumnos = [a for a in alumnos if a.estado_mensualidad == estado_mensualidad]

    return alumnos, None


def _filtros_contexto():
    return dict(
        categorias=Categoria.query.order_by(Categoria.nombre).all(),
        equipos=Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all(),
        campeonatos=Campeonato.query.order_by(Campeonato.nombre).all(),
        posiciones=POSICIONES, becas=BECAS, sexos=SEXOS, turnos=TURNOS,
        estados=ESTADOS_ALUMNO, estados_pago=ESTADOS_MENSUALIDAD,
    )


@bp.route("/")
def listar():
    alumnos, paginacion = _filtrar_alumnos(request.args, paginar=True)
    contexto = dict(
        alumnos=alumnos, paginacion=paginacion,
        base_paginacion=urlencode([
            (clave, valor) for clave, valores in request.args.lists()
            if clave != "page" for valor in valores
        ]),
        filtros=request.args, **_filtros_contexto()
    )
    if request.headers.get("HX-Request"):
        return render_template("alumnos/_tabla.html", **contexto)
    return render_template("alumnos/listar.html", **contexto)


@bp.route("/asistencias")
def asistencias():
    hoy = date.today()
    periodo = request.args.get("periodo", "semana")
    if periodo not in {"semana", "ultimas3", "ultimas10", "mes", "rango", "todas"}:
        periodo = "semana"
    id_alumno = request.args.get("id_alumno", type=int)
    id_categoria = request.args.get("id_categoria", type=int)
    id_equipo = request.args.get("id_equipo", type=int)
    turno = request.args.get("turno", "")
    estado_asistencia = request.args.get("estado_asistencia", "")

    consulta = AsistenciaEntrenamiento.query.join(AsistenciaEntrenamiento.sesion).join(
        AsistenciaEntrenamiento.alumno
    )
    if id_alumno:
        consulta = consulta.filter(AsistenciaEntrenamiento.id_alumno == id_alumno)
    if id_categoria:
        consulta = consulta.filter(Alumno.id_categoria == id_categoria)
    if id_equipo:
        consulta = consulta.filter(Alumno.equipos.any(Equipo.id_equipo == id_equipo))
    if turno:
        consulta = consulta.filter(Alumno.turno == turno)
    if estado_asistencia in {"Presente", "Ausente", "Justificado", "Tarde"}:
        consulta = consulta.filter(AsistenciaEntrenamiento.estado == estado_asistencia)

    fecha_desde = fecha_hasta = None
    if periodo == "semana":
        fecha_desde = hoy - timedelta(days=hoy.weekday())
        fecha_hasta = fecha_desde + timedelta(days=6)
    elif periodo == "mes":
        fecha_desde = hoy.replace(day=1)
        fecha_hasta = (fecha_desde + relativedelta(months=1)) - timedelta(days=1)
    elif periodo == "rango":
        try:
            fecha_desde = fecha_iso(request.args.get("fecha_desde"), "Fecha desde", requerida=False)
            fecha_hasta = fecha_iso(request.args.get("fecha_hasta"), "Fecha hasta", requerida=False)
        except ErrorValidacion as error:
            flash(str(error), "warning")
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(SesionEntrenamiento.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(SesionEntrenamiento.fecha <= fecha_hasta)

    consulta = consulta.order_by(
        SesionEntrenamiento.fecha.desc(), AsistenciaEntrenamiento.registrado_en.desc()
    )
    if periodo == "ultimas3":
        registros = consulta.limit(3).all()
    elif periodo == "ultimas10":
        registros = consulta.limit(10).all()
    else:
        registros = consulta.all()

    resumen = {
        estado: sum(1 for registro in registros if registro.estado == estado)
        for estado in ("Presente", "Tarde", "Ausente", "Justificado")
    }
    total = len(registros)
    porcentaje = round((resumen["Presente"] + resumen["Tarde"]) * 100 / total) if total else 0
    alumno_seleccionado = db.session.get(Alumno, id_alumno) if id_alumno else None
    return render_template(
        "alumnos/asistencias.html", registros=registros, resumen=resumen, total=total,
        porcentaje=porcentaje, periodo=periodo, alumno_seleccionado=alumno_seleccionado,
        alumnos=Alumno.query.order_by(Alumno.apellido, Alumno.nombre).all(),
        categorias=Categoria.query.order_by(Categoria.nombre).all(),
        equipos=Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all(),
        turnos=TURNOS, filtros=request.args, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        dias_semana=("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"),
    )


@bp.route("/exportar")
def exportar_excel():
    alumnos, _ = _filtrar_alumnos(request.args)
    encabezados, filas = _datos_exportacion_alumnos(alumnos)
    titulo, nombre_base = _nombre_exportacion("Listado de alumnos")
    _, logo_configurado = configuracion_y_logo()
    logo_path = logo_configurado if request.args.get("incluir_escudo") else None
    buffer = exportar_tabla_excel(titulo, encabezados, filas, logo_path=logo_path)
    nombre = f"{nombre_base}.xlsx"
    return enviar_buffer(
        buffer, "alumnos", nombre,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/exportar.pdf")
def exportar_pdf():
    alumnos, _ = _filtrar_alumnos(request.args)
    encabezados, filas = _datos_exportacion_alumnos(alumnos)
    titulo, nombre_base = _nombre_exportacion("Listado de alumnos")
    _, logo_configurado = configuracion_y_logo()
    logo_path = logo_configurado if request.args.get("incluir_escudo") else None
    buffer = generar_tabla_pdf(
        titulo, encabezados, filas, orientacion="vertical",
        tamano_pagina="carta", tamano_letra=12, logo_path=logo_path,
    )
    nombre = f"{nombre_base}.pdf"
    return enviar_buffer(buffer, "alumnos", nombre, "application/pdf")


@bp.route("/equipos-por-categoria")
def equipos_por_categoria():
    seleccionados_raw = request.args.get("seleccionados", "")
    seleccionados = [int(x) for x in seleccionados_raw.split(",") if x]
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()
    return render_template("alumnos/_select_equipos.html", equipos=equipos, seleccionados=seleccionados)


@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()

    if request.method == "POST":
        try:
            datos, id_categoria_manual, equipos_seleccionados = _datos_alumno_formulario()
            if current_app.config.get("AUTH_REQUIRED", True) and datos.get("beca") != "Ninguna" and not tiene_permiso("gestionar_becas"):
                raise ErrorValidacion("No tiene permiso para autorizar una beca.")
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "alumnos/form.html", alumno=None, categorias=categorias, equipos=equipos,
                estados=ESTADOS_ALUMNO, posiciones=POSICIONES, piernas=PIERNAS,
                sexos=SEXOS, becas=BECAS, turnos=TURNOS,
            )
        alumno = Alumno(**datos)
        if id_categoria_manual:
            alumno.id_categoria = id_categoria_manual
            alumno.categoria_manual = True
        else:
            cat = categoria_automatica_por_edad(alumno.fecha_nacimiento)
            alumno.id_categoria = cat.id_categoria if cat else None

        foto = request.files.get("foto")
        nombre_foto = _guardar_foto(foto)
        if nombre_foto:
            alumno.foto = nombre_foto

        alumno.equipos = equipos_seleccionados

        db.session.add(alumno)
        db.session.flush()
        _crear_ciclo_inicial(alumno, equipos_seleccionados)
        _sincronizar_tutores(alumno)
        db.session.add(Auditoria(
            modulo="Alumnos", accion="Crear", entidad="Alumno",
            id_entidad=alumno.id_alumno, detalle=alumno.nombre_completo,
        ))
        db.session.commit()
        posible_duplicado = Alumno.query.filter(
            Alumno.id_alumno != alumno.id_alumno,
            db.func.lower(Alumno.nombre) == alumno.nombre.lower(),
            db.func.lower(Alumno.apellido) == alumno.apellido.lower(),
            Alumno.fecha_nacimiento == alumno.fecha_nacimiento,
        ).first()
        if posible_duplicado:
            flash(
                f"Advertencia: existe una ficha similar ({posible_duplicado.codigo_interno}).",
                "warning",
            )
        flash(f"Alumno {alumno.nombre_completo} registrado correctamente.", "success")
        return redirect(url_for("alumnos.detalle", id_alumno=alumno.id_alumno))

    return render_template(
        "alumnos/form.html", alumno=None, categorias=categorias, equipos=equipos,
        estados=ESTADOS_ALUMNO, posiciones=POSICIONES, piernas=PIERNAS, sexos=SEXOS, becas=BECAS, turnos=TURNOS,
    )


@bp.route("/<int:id_alumno>")
def detalle(id_alumno):
    alumno = Alumno.query.get_or_404(id_alumno)
    hoy = date.today()
    try:
        proximo_cumple = alumno.fecha_nacimiento.replace(year=hoy.year)
    except ValueError:
        proximo_cumple = date(hoy.year, 2, 28)
    if proximo_cumple < hoy:
        try:
            proximo_cumple = alumno.fecha_nacimiento.replace(year=hoy.year + 1)
        except ValueError:
            proximo_cumple = date(hoy.year + 1, 2, 28)
    dias_cumple = (proximo_cumple - hoy).days
    edad_proxima = alumno.edad + (0 if dias_cumple == 0 else 1)
    categoria_proxima = (
        categoria_automatica_por_edad(
            alumno.fecha_nacimiento - relativedelta(years=1)
        )
        if dias_cumple <= 30 else None
    )
    asistencias = sorted(
        alumno.asistencias_entrenamiento,
        key=lambda registro: (
            registro.sesion.fecha, registro.sesion.entrenamiento.hora_inicio,
            registro.id_asistencia,
        ),
        reverse=True,
    )
    resumen_asistencia = {
        estado: sum(1 for registro in asistencias if registro.estado == estado)
        for estado in ("Presente", "Tarde", "Ausente", "Justificado")
    }
    total_asistencias = len(asistencias)
    asistencias_efectivas = resumen_asistencia["Presente"] + resumen_asistencia["Tarde"]
    porcentaje_asistencia = round(asistencias_efectivas * 100 / total_asistencias) if total_asistencias else 0

    condiciones_programacion = []
    if alumno.id_categoria:
        condiciones_programacion.append(Entrenamiento.id_categoria == alumno.id_categoria)
    ids_equipos = [equipo.id_equipo for equipo in alumno.equipos]
    if ids_equipos:
        condiciones_programacion.append(Entrenamiento.id_equipo.in_(ids_equipos))
    entrenamientos_asignados = (
        Entrenamiento.query.filter(
            Entrenamiento.activo.is_(True), db.or_(*condiciones_programacion)
        ).order_by(Entrenamiento.dia_semana, Entrenamiento.hora_inicio).all()
        if condiciones_programacion else []
    )
    if alumno.turno:
        entrenamientos_asignados = [
            entrenamiento for entrenamiento in entrenamientos_asignados
            if entrenamiento.turno == alumno.turno
        ]
    return render_template(
        "alumnos/detalle.html", alumno=alumno,
        proximo_cumple=proximo_cumple, dias_cumple=dias_cumple,
        edad_proxima=edad_proxima, categoria_proxima=categoria_proxima,
        asistencias=asistencias, resumen_asistencia=resumen_asistencia,
        total_asistencias=total_asistencias, porcentaje_asistencia=porcentaje_asistencia,
        entrenamientos_asignados=entrenamientos_asignados,
        dias_semana=("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"),
    )


@bp.route("/<int:id_alumno>/foto")
def foto_privada(id_alumno):
    alumno = Alumno.query.get_or_404(id_alumno)
    if not alumno.foto:
        abort(404)
    ruta = os.path.join(current_app.config["UPLOAD_FOLDER"], alumno.foto)
    if not os.path.isfile(ruta):
        abort(404)
    return send_file(ruta, conditional=True, max_age=0)


@bp.route("/<int:id_alumno>/ficha.pdf")
def ficha_pdf(id_alumno):
    alumno = Alumno.query.get_or_404(id_alumno)
    config, logo_path = configuracion_y_logo()
    foto_path = (
        os.path.join(current_app.config["UPLOAD_FOLDER"], alumno.foto)
        if alumno.foto else None
    )
    buffer = generar_ficha_alumno(
        alumno,
        logo_path=logo_path,
        foto_path=foto_path,
        gestion=config.gestion_ficha,
        nombre_academia=config.nombre_academia,
        eslogan=config.eslogan,
    )
    nombre = secure_filename(f"ficha_{alumno.nombre}_{alumno.apellido}") + ".pdf"
    return enviar_buffer(buffer, "perfiles", nombre, "application/pdf")


@bp.route("/<int:id_alumno>/editar", methods=["GET", "POST"])
def editar(id_alumno):
    alumno = Alumno.query.get_or_404(id_alumno)
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    equipos = Equipo.query.filter_by(es_rival=False).order_by(Equipo.nombre).all()

    if request.method == "POST":
        anterior = {
            "categoria": alumno.id_categoria,
            "estado": alumno.estado,
            "equipos": sorted(e.id_equipo for e in alumno.equipos),
        }
        try:
            datos, id_categoria_manual, equipos_seleccionados = _datos_alumno_formulario(id_alumno)
            if current_app.config.get("AUTH_REQUIRED", True) and (datos.get("beca"), datos.get("beca_fecha_fin")) != (alumno.beca, alumno.beca_fecha_fin) and not tiene_permiso("gestionar_becas"):
                raise ErrorValidacion("No tiene permiso para modificar una beca.")
            fecha_reactivacion = None
            fecha_retiro = None
            motivo_cambio = texto_opcional(
                request.form.get("motivo_cambio"), "Motivo", 255
            )
            if alumno.estado != datos["estado"] and not motivo_cambio:
                raise ErrorValidacion("El motivo es obligatorio al cambiar el estado del alumno.")
            if alumno.estado == "Activo" and datos["estado"] == "Retirado":
                fecha_retiro = fecha_no_futura(
                    fecha_iso(request.form.get("fecha_retiro"), "Fecha de retiro"),
                    "Fecha de retiro",
                )
            if alumno.estado == "Retirado" and datos["estado"] == "Activo":
                fecha_reactivacion = fecha_no_futura(
                    fecha_iso(
                        request.form.get("fecha_reactivacion"),
                        "Fecha de reactivación",
                    ),
                    "Fecha de reactivación",
                )
                if alumno.fecha_retiro and fecha_reactivacion < alumno.fecha_retiro:
                    raise ErrorValidacion(
                        "La reactivación no puede ser anterior a la fecha de retiro."
                    )
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "alumnos/form.html", alumno=alumno, categorias=categorias, equipos=equipos,
                estados=ESTADOS_ALUMNO, posiciones=POSICIONES, piernas=PIERNAS,
                sexos=SEXOS, becas=BECAS, turnos=TURNOS, hoy=date.today().isoformat(),
            )
        categoria_anterior = alumno.id_categoria
        equipos_anteriores = {e.id_equipo for e in alumno.equipos}
        beca_anterior = alumno.beca
        beca_fin_anterior = alumno.beca_fecha_fin
        for campo, valor in datos.items():
            setattr(alumno, campo, valor)
        if id_categoria_manual:
            alumno.id_categoria = id_categoria_manual
            alumno.categoria_manual = True
        else:
            cat = categoria_automatica_por_edad(alumno.fecha_nacimiento)
            alumno.id_categoria = cat.id_categoria if cat else None
            alumno.categoria_manual = False

        foto = request.files.get("foto")
        nombre_foto = _guardar_foto(foto)
        if nombre_foto:
            foto_anterior = alumno.foto
            alumno.foto = nombre_foto
            _eliminar_foto(foto_anterior)

        alumno.equipos = equipos_seleccionados
        _sincronizar_tutores(alumno)

        hoy = date.today()
        usuario_id = _usuario_actual_id()
        motivo_historial = motivo_cambio or "Actualización de ficha"
        if alumno.id_categoria != categoria_anterior:
            vigente = HistorialCategoriaAlumno.query.filter_by(id_alumno=alumno.id_alumno, fecha_fin=None).first()
            if vigente:
                vigente.fecha_fin = hoy
            if alumno.id_categoria:
                db.session.add(HistorialCategoriaAlumno(
                    id_alumno=alumno.id_alumno, id_categoria=alumno.id_categoria,
                    fecha_inicio=hoy, tipo_asignacion="Manual" if alumno.categoria_manual else "Automática",
                    motivo=motivo_historial, id_usuario=usuario_id,
                ))
        equipos_nuevos = {e.id_equipo for e in equipos_seleccionados}
        for registro in HistorialEquipoAlumno.query.filter_by(id_alumno=alumno.id_alumno, fecha_fin=None).all():
            if registro.id_equipo not in equipos_nuevos:
                registro.fecha_fin, registro.estado, registro.motivo_salida = hoy, "Finalizada", motivo_historial
        gestion = Configuracion.obtener().gestion_ficha
        for indice, equipo in enumerate(equipos_seleccionados):
            if equipo.id_equipo not in equipos_anteriores:
                db.session.add(HistorialEquipoAlumno(
                    id_alumno=alumno.id_alumno, id_equipo=equipo.id_equipo, gestion=gestion,
                    fecha_inicio=hoy, principal=indice == 0, id_usuario=usuario_id,
                ))
        inscripcion = InscripcionGestion.query.filter_by(id_alumno=alumno.id_alumno, gestion=gestion).first()
        if inscripcion:
            inscripcion.id_categoria = alumno.id_categoria
            inscripcion.id_equipo_principal = equipos_seleccionados[0].id_equipo if equipos_seleccionados else None
            inscripcion.estado = "Activa" if alumno.estado == "Activo" else "Retirada"

        if alumno.beca != beca_anterior or alumno.beca_fecha_fin != beca_fin_anterior:
            BecaHistorial.query.filter_by(id_alumno=alumno.id_alumno, estado="Activa").update(
                {"fecha_fin": hoy, "estado": "Finalizada"}
            )
            porcentaje = {"Ninguna": 0, "Media": 50, "Completa": 100}[alumno.beca]
            db.session.add(BecaHistorial(
                id_alumno=alumno.id_alumno, porcentaje=porcentaje,
                fecha_inicio=date.today(), fecha_fin=alumno.beca_fecha_fin,
                estado="Activa", id_usuario=usuario_id,
                motivo=motivo_cambio or "ActualizaciÃ³n de beca",
            ))
            if inscripcion:
                inscripcion.porcentaje_beca = porcentaje

        if fecha_retiro:
            alumno.fecha_retiro = fecha_retiro
            db.session.add(HistorialAlumno(
                id_alumno=alumno.id_alumno, tipo="retiro",
                valor_anterior=None, valor_nuevo=fecha_retiro.isoformat(),
                motivo=motivo_cambio,
            ))

        if fecha_reactivacion:
            fecha_base_anterior = alumno.fecha_base_pago
            alumno.fecha_ultima_reactivacion = fecha_reactivacion
            alumno.fecha_base_pago = fecha_reactivacion
            db.session.add(HistorialAlumno(
                id_alumno=alumno.id_alumno,
                tipo="reactivacion",
                valor_anterior=fecha_base_anterior.isoformat() if fecha_base_anterior else None,
                valor_nuevo=fecha_reactivacion.isoformat(),
                motivo=texto_opcional(
                    request.form.get("motivo_cambio"), "Motivo", 255
                ) or "Reactivación del alumno y apertura de nuevo ciclo de mensualidad",
            ))

        nuevo = {
            "categoria": alumno.id_categoria,
            "estado": alumno.estado,
            "equipos": sorted(e.id_equipo for e in alumno.equipos),
        }
        for tipo in ("categoria", "estado", "equipos"):
            if anterior[tipo] != nuevo[tipo]:
                db.session.add(HistorialAlumno(
                    id_alumno=alumno.id_alumno, tipo=tipo,
                    valor_anterior=str(anterior[tipo]), valor_nuevo=str(nuevo[tipo]),
                    motivo=texto_opcional(request.form.get("motivo_cambio"), "Motivo", 255),
                ))
        db.session.add(Auditoria(
            modulo="Alumnos", accion="Editar", entidad="Alumno",
            id_entidad=alumno.id_alumno, detalle=alumno.nombre_completo,
        ))

        db.session.commit()
        flash("Datos del alumno actualizados.", "success")
        return redirect(url_for("alumnos.detalle", id_alumno=alumno.id_alumno))

    return render_template(
        "alumnos/form.html", alumno=alumno, categorias=categorias, equipos=equipos,
        estados=ESTADOS_ALUMNO, posiciones=POSICIONES, piernas=PIERNAS,
        sexos=SEXOS, becas=BECAS, turnos=TURNOS, hoy=date.today().isoformat(),
    )


@bp.route("/<int:id_alumno>/recalcular-categoria", methods=["POST"])
def recalcular_categoria(id_alumno):
    alumno = Alumno.query.get_or_404(id_alumno)
    cat = categoria_automatica_por_edad(alumno.fecha_nacimiento)
    alumno.id_categoria = cat.id_categoria if cat else alumno.id_categoria
    alumno.categoria_manual = False
    db.session.commit()
    flash("Categoría recalculada automáticamente según la edad.", "success")
    return redirect(url_for("alumnos.detalle", id_alumno=alumno.id_alumno))


@bp.route("/<int:id_alumno>/eliminar", methods=["POST"])
def eliminar(id_alumno):
    alumno = Alumno.query.get_or_404(id_alumno)
    if alumno.pagos:
        flash("No se puede eliminar: el alumno tiene pagos registrados. Márquelo como 'Retirado' en su lugar.", "danger")
        return redirect(url_for("alumnos.detalle", id_alumno=id_alumno))
    foto = alumno.foto
    db.session.add(Auditoria(
        modulo="Alumnos", accion="Eliminar", entidad="Alumno",
        id_entidad=alumno.id_alumno, detalle=alumno.nombre_completo,
    ))
    db.session.delete(alumno)
    db.session.commit()
    _eliminar_foto(foto)
    flash("Alumno eliminado.", "success")
    return redirect(url_for("alumnos.listar"))
