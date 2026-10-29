import os
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from urllib.parse import urlencode
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, send_file, current_app, abort, session
)
from werkzeug.utils import secure_filename
from dateutil.relativedelta import relativedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    Alumno, Pago, Categoria, MODOS_PAGO, ESTADOS_PAGO, BECAS, SEXOS,
    AnulacionPago, HistorialAlumno, Auditoria, MovimientoContable, ahora_utc,
    Obligacion, AplicacionPago,
)
from app.utils.backup import crear_respaldo
from app.utils.reglas import (
    siguiente_mes_a_pagar, calcular_vencimiento, ya_existe_pago_mes, calcular_monto_pago
)
from app.utils.pdfs import generar_recibo_pago
from app.utils.personalizacion import configuracion_y_logo
from app.utils.descargas import enviar_buffer
from app.utils.pdf_tablas import generar_tabla_pdf
from app.utils.excel import exportar_pagos_excel, exportar_tabla_excel
from app.utils.validacion import (
    ErrorValidacion, fecha_iso, fecha_no_futura, mes_iso, opcion,
    texto_opcional, texto_requerido,
)

bp = Blueprint("pagos", __name__, url_prefix="/pagos")


COLUMNAS_EXPORTACION = {
    "id_pago": ("ID Pago", lambda p: p.id_pago),
    "alumno": ("Alumno", lambda p: p.alumno.nombre_completo),
    "ci": ("CI", lambda p: p.alumno.ci or "-"),
    "categoria": ("Categoría", lambda p: p.alumno.categoria.nombre if p.alumno.categoria else "-"),
    "mes": ("Mes pagado", lambda p: p.mes_pagado),
    "fecha_pago": ("Fecha de pago", lambda p: p.fecha_pago.strftime("%d/%m/%Y")),
    "hora": ("Hora", lambda p: p.hora_registro.strftime("%H:%M") if p.hora_registro else "-"),
    "vencimiento": ("Vencimiento", lambda p: p.fecha_vencimiento.strftime("%d/%m/%Y")),
    "estado": ("Estado", lambda p: p.estado),
    "modo": ("Modo de pago", lambda p: "Beca" if p.es_beca else p.modo_pago),
    "beca": ("Beca alumno", lambda p: p.alumno.beca),
    "monto": ("Monto", lambda p: f"{p.monto:.2f}"),
    "operacion_qr": ("Operación QR", lambda p: p.numero_operacion or "-"),
}


def _datos_exportacion_pagos(pagos):
    solicitadas = request.args.getlist("columnas")
    claves = [clave for clave in solicitadas if clave in COLUMNAS_EXPORTACION]
    if not claves:
        abort(400, description="Debe seleccionar al menos una columna para exportar.")
    encabezados = ["N°"] + [COLUMNAS_EXPORTACION[clave][0] for clave in claves]
    filas = [
        [numero] + [COLUMNAS_EXPORTACION[clave][1](pago) for clave in claves]
        for numero, pago in enumerate(pagos, start=1)
    ]
    return encabezados, filas


def _nombre_exportacion(predeterminado):
    solicitado = request.args.get("nombre_archivo", "").strip()
    titulo = solicitado[:100] if solicitado else predeterminado
    nombre_seguro = secure_filename(titulo).rsplit(".", 1)[0] or secure_filename(predeterminado)
    return titulo, nombre_seguro


MESES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _datos_resumen_seis_meses(args):
    """Construye una matriz por alumno desde el mes actual hasta cinco meses atrás."""
    nombre = args.get("nombre", "").strip()
    apellido = args.get("apellido", "").strip()
    id_categoria = args.get("id_categoria", type=int)
    edad = args.get("edad", type=int)
    beca = args.get("beca", "")
    sexo = args.get("sexo", "")
    estado_alumno = args.get("estado_alumno", "Activo")

    consulta = Alumno.query
    if nombre:
        consulta = consulta.filter(Alumno.nombre.ilike(f"%{nombre}%"))
    if apellido:
        consulta = consulta.filter(Alumno.apellido.ilike(f"%{apellido}%"))
    if id_categoria:
        consulta = consulta.filter(Alumno.id_categoria == id_categoria)
    if beca:
        consulta = consulta.filter(Alumno.beca == beca)
    if sexo:
        consulta = consulta.filter(Alumno.sexo == sexo)
    if estado_alumno:
        consulta = consulta.filter(Alumno.estado == estado_alumno)

    alumnos = consulta.order_by(Alumno.apellido, Alumno.nombre).all()
    if edad is not None:
        alumnos = [alumno for alumno in alumnos if alumno.edad == edad]

    # Cuando hay filtros propios de pagos, conserva únicamente alumnos que
    # tengan al menos un pago coincidente con esos filtros.
    filtros_pago = ("estado", "fecha_vencimiento", "fecha_pago", "mes_vencimiento")
    if any(args.get(filtro, "") for filtro in filtros_pago):
        ids_coincidentes = {pago.id_alumno for pago in _filtrar_pagos(args)}
        alumnos = [alumno for alumno in alumnos if alumno.id_alumno in ids_coincidentes]

    mes_actual = date.today().replace(day=1)
    meses = [mes_actual - relativedelta(months=desfase) for desfase in range(5, -1, -1)]
    claves_mes = [mes.strftime("%Y-%m") for mes in meses]
    encabezados = ["N°", "Alumno"] + [f"{MESES_ES[mes.month - 1]} {mes.year}" for mes in meses]

    ids_alumnos = [alumno.id_alumno for alumno in alumnos]
    pagos = []
    if ids_alumnos:
        pagos = Pago.query.filter(
            Pago.eliminado_en.is_(None),
            Pago.id_alumno.in_(ids_alumnos),
            Pago.mes_pagado.in_(claves_mes),
        ).all()
    pagos_por_alumno_mes = {(pago.id_alumno, pago.mes_pagado): pago for pago in pagos}

    filas = []
    for numero, alumno in enumerate(alumnos, start=1):
        fila = [numero, alumno.nombre_completo]
        for clave_mes in claves_mes:
            pago = pagos_por_alumno_mes.get((alumno.id_alumno, clave_mes))
            fila.append(f"{pago.estado} - {pago.fecha_pago.strftime('%d/%m/%Y')}" if pago else "Sin pago")
        filas.append(fila)
    return encabezados, filas, meses


def _filtrar_pagos(args, paginar=False):
    """Aplica todos los filtros del módulo de pagos y devuelve la lista resultante."""
    nombre = args.get("nombre", "").strip()
    apellido = args.get("apellido", "").strip()
    id_categoria = args.get("id_categoria", type=int)
    edad = args.get("edad", type=int)
    beca = args.get("beca", "")
    sexo = args.get("sexo", "")
    estado_alumno = args.get("estado_alumno", "Activo")
    estado = args.get("estado", "")
    fecha_vencimiento = args.get("fecha_vencimiento", "")
    fecha_pago = args.get("fecha_pago", "")
    mes_vencimiento = args.get("mes_vencimiento", "")

    query = Pago.query.join(Alumno).options(
        joinedload(Pago.alumno).joinedload(Alumno.categoria)
    )
    if estado == "Anulado":
        query = query.filter(Pago.eliminado_en.is_not(None))
    else:
        query = query.filter(Pago.eliminado_en.is_(None))
    if nombre:
        query = query.filter(Alumno.nombre.ilike(f"%{nombre}%"))
    if apellido:
        query = query.filter(Alumno.apellido.ilike(f"%{apellido}%"))
    if id_categoria:
        query = query.filter(Alumno.id_categoria == id_categoria)
    if beca:
        query = query.filter(Alumno.beca == beca)
    if sexo:
        query = query.filter(Alumno.sexo == sexo)
    if estado_alumno:
        query = query.filter(Alumno.estado == estado_alumno)
    if fecha_vencimiento:
        query = query.filter(Pago.fecha_vencimiento == datetime.strptime(fecha_vencimiento, "%Y-%m-%d").date())
    if fecha_pago:
        query = query.filter(Pago.fecha_pago == datetime.strptime(fecha_pago, "%Y-%m-%d").date())
    if edad is not None and edad >= 0:
        hoy = date.today()
        nacimiento_maximo = hoy - relativedelta(years=edad)
        nacimiento_minimo = hoy - relativedelta(years=edad + 1) + timedelta(days=1)
        query = query.filter(Alumno.fecha_nacimiento.between(
            nacimiento_minimo, nacimiento_maximo
        ))
    if estado:
        hoy = date.today()
        if estado == "Anulado":
            pass
        elif estado == "Pagado":
            query = query.filter(Pago.fecha_vencimiento < hoy)
        elif estado == "Próximo a vencer":
            query = query.filter(
                Pago.fecha_vencimiento >= hoy,
                Pago.fecha_vencimiento <= hoy + timedelta(days=5),
            )
        elif estado == "Vigente":
            query = query.filter(Pago.fecha_vencimiento > hoy + timedelta(days=5))
    if mes_vencimiento:
        inicio_mes = datetime.strptime(mes_vencimiento + "-01", "%Y-%m-%d").date()
        fin_mes = inicio_mes + relativedelta(months=1)
        query = query.filter(
            Pago.fecha_vencimiento >= inicio_mes, Pago.fecha_vencimiento < fin_mes
        )
    query = query.order_by(
        Pago.fecha_pago.desc(),
        Pago.hora_registro.desc(),
        Pago.id_pago.desc(),
    )
    if paginar:
        pagina = max(args.get("page", 1, type=int), 1)
        paginacion = query.paginate(
            page=pagina, per_page=current_app.config.get("ITEMS_PER_PAGE", 40),
            error_out=False,
        )
        return paginacion.items, paginacion
    return query.all()


def _filtros_contexto():
    return dict(
        categorias=Categoria.query.order_by(Categoria.nombre).all(),
        becas=BECAS, sexos=SEXOS, estados_pago=ESTADOS_PAGO,
    )


@bp.route("/")
def listar():
    pagos, paginacion = _filtrar_pagos(request.args, paginar=True)
    contexto = dict(
        pagos=pagos, paginacion=paginacion,
        base_paginacion=urlencode([
            (clave, valor) for clave, valores in request.args.lists()
            if clave != "page" for valor in valores
        ]),
        filtros=request.args, **_filtros_contexto()
    )
    if request.headers.get("HX-Request"):
        return render_template("pagos/_tabla.html", **contexto)
    return render_template("pagos/listar.html", **contexto)


@bp.route("/alumno/<int:id_alumno>/nuevo", methods=["GET", "POST"])
def crear(id_alumno):
    alumno = Alumno.query.get_or_404(id_alumno)

    # La restricción se aplica en el servidor para impedir pagos incluso si
    # alguien intenta acceder directamente a la URL o enviar un formulario.
    if alumno.estado == "Retirado":
        flash("No se puede registrar un pago porque el alumno está retirado. Cámbielo a Activo para continuar.", "warning")
        return redirect(url_for("alumnos.detalle", id_alumno=alumno.id_alumno))

    mes_sugerido = siguiente_mes_a_pagar(alumno)
    es_primer_pago = alumno.fecha_base_pago is None and not any(p.activo for p in alumno.pagos)

    if request.method == "POST":
        try:
            mes_pagado = mes_iso(request.form.get("mes_pagado"))
            modo_pago = opcion(
                request.form.get("modo_pago", "Efectivo"), MODOS_PAGO, "Modo de pago"
            )
            numero_operacion = texto_opcional(
                request.form.get("numero_operacion"), "Número de operación QR", 80
            )
            if modo_pago == "QR" and not numero_operacion:
                raise ErrorValidacion("Registre el número de operación o referencia del QR.")
            if modo_pago != "QR":
                numero_operacion = None
            if numero_operacion and Pago.query.filter(
                Pago.numero_operacion == numero_operacion,
                Pago.eliminado_en.is_(None),
            ).first():
                raise ErrorValidacion("Ese número de operación QR ya fue registrado.")
            if es_primer_pago:
                fecha_pago = fecha_no_futura(
                    fecha_iso(request.form.get("fecha_pago"), "Fecha de pago"),
                    "Fecha de pago",
                )
            else:
                fecha_pago = date.today()
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "pagos/form.html", alumno=alumno, mes_sugerido=mes_sugerido,
                es_primer_pago=es_primer_pago, modos=MODOS_PAGO,
                hoy=date.today().isoformat(),
            )

        obligacion = Obligacion.query.filter_by(
            id_alumno=alumno.id_alumno, concepto="Mensualidad", periodo=mes_pagado
        ).first()
        if obligacion and obligacion.saldo <= 0:
            flash(f"La mensualidad {mes_pagado} ya está completamente cubierta.", "danger")
            return redirect(url_for("pagos.crear", id_alumno=id_alumno))
        ultimo_registro = Pago.query.order_by(Pago.creado_en.desc()).first()
        if ultimo_registro and ultimo_registro.creado_en:
            if ahora_utc() + timedelta(minutes=5) < ultimo_registro.creado_en:
                flash(
                    "El reloj de Windows parece estar atrasado respecto del último pago. "
                    "Corrija fecha y hora antes de continuar.",
                    "danger",
                )
                return redirect(url_for("pagos.crear", id_alumno=id_alumno))

        # Primera vez: la fecha de pago define la fecha base de vencimientos futuros.
        if es_primer_pago:
            alumno.fecha_base_pago = fecha_pago

        es_beca = alumno.beca_vigente == "Completa"
        if request.form.get("es_beca") == "on" and not es_beca:
            flash("No puede cubrir esta mensualidad como beca porque el alumno no tiene una beca completa vigente.", "danger")
            return redirect(url_for("pagos.crear", id_alumno=id_alumno))

        vencimiento = calcular_vencimiento(alumno, fecha_pago, mes_pagado)
        monto_tarifa = calcular_monto_pago(alumno, es_beca, mes_pagado)
        try:
            descuento = Decimal(request.form.get("descuento", "0") or "0").quantize(Decimal("0.01"))
            recargo = Decimal(request.form.get("recargo", "0") or "0").quantize(Decimal("0.01"))
            if descuento < 0 or recargo < 0 or descuento > monto_tarifa:
                raise ValueError
        except (ValueError, ArithmeticError):
            flash("Revise el descuento y el recargo.", "danger")
            return redirect(url_for("pagos.crear", id_alumno=id_alumno))
        if not obligacion:
            obligacion = Obligacion(
                id_alumno=alumno.id_alumno, concepto="Mensualidad", periodo=mes_pagado,
                monto_original=monto_tarifa, descuento=descuento, recargo=recargo,
                cubierto_beca=es_beca, fecha_vencimiento=vencimiento,
            )
            db.session.add(obligacion)
            db.session.flush()
        saldo = obligacion.saldo
        try:
            solicitado = request.form.get("monto_abono", "").strip()
            monto = Decimal(solicitado).quantize(Decimal("0.01")) if solicitado else saldo
            if (solicitado and monto <= 0) or monto > saldo:
                raise ValueError
            if es_beca:
                monto = Decimal("0.00")
        except (ValueError, ArithmeticError):
            db.session.rollback()
            flash(f"El abono debe ser mayor a cero y no superar el saldo de {saldo:.2f}.", "danger")
            return redirect(url_for("pagos.crear", id_alumno=id_alumno))

        pago = Pago(
            id_alumno=alumno.id_alumno,
            es_beca=es_beca,
            fecha_pago=fecha_pago,
            hora_registro=datetime.now().time(),
            fecha_vencimiento=vencimiento,
            mes_pagado=mes_pagado,
            modo_pago=modo_pago,
            monto=monto,
            numero_operacion=numero_operacion,
        )
        db.session.add(pago)
        db.session.flush()
        db.session.add(AplicacionPago(
            id_obligacion=obligacion.id_obligacion, id_pago=pago.id_pago, monto=monto
        ))
        if not es_beca and monto > 0:
            db.session.add(MovimientoContable(
                tipo="Ingreso", categoria="Mensualidades",
                concepto=f"Mensualidad {mes_pagado} - {alumno.nombre_completo}",
                monto=monto, fecha=fecha_pago, modo_pago=modo_pago,
                numero_operacion=numero_operacion,
                origen_tipo="Pago", origen_id=pago.id_pago,
            ))
        alumno_codigo = alumno.codigo_interno or ""
        numero_recibo = f"{pago.id_pago:06d}"
        db.session.add(Auditoria(
            modulo="Pagos", accion="Registrar", entidad="Pago",
            id_entidad=pago.id_pago,
            id_usuario=session.get("id_usuario"),
            valor_anterior=None,
            valor_nuevo=f"Recibo #{numero_recibo} | {alumno.nombre_completo} ({alumno_codigo}) | Mes: {mes_pagado} | Bs. {monto:.2f} ({modo_pago})",
            detalle=f"Registro de pago #{numero_recibo} para {alumno.nombre_completo} (Mes: {mes_pagado}, Bs. {monto:.2f}, {modo_pago})",
        ))
        anulacion_previa = (
            AnulacionPago.query.join(Pago, AnulacionPago.id_pago == Pago.id_pago)
            .filter(
                Pago.id_alumno == alumno.id_alumno,
                Pago.mes_pagado == mes_pagado,
                AnulacionPago.id_pago_reemplazo.is_(None),
            )
            .order_by(AnulacionPago.creado_en.desc())
            .first()
        )
        if anulacion_previa:
            anulacion_previa.id_pago_reemplazo = pago.id_pago
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                f"Ya existe un pago activo para {mes_pagado}. No se registró un duplicado.",
                "danger",
            )
            return redirect(url_for("pagos.crear", id_alumno=id_alumno))
        flash(f"Pago de {mes_pagado} registrado. Vence el {vencimiento.strftime('%d/%m/%Y')}.", "success")
        return redirect(url_for("pagos.comprobante", id_pago=pago.id_pago))

    return render_template(
        "pagos/form.html", alumno=alumno, mes_sugerido=mes_sugerido,
        es_primer_pago=es_primer_pago, modos=MODOS_PAGO, hoy=date.today().isoformat(),
    )


@bp.route("/<int:id_pago>/comprobante")
def comprobante(id_pago):
    pago = Pago.query.filter(Pago.eliminado_en.is_(None)).filter_by(id_pago=id_pago).first_or_404()
    return render_template("pagos/comprobante.html", pago=pago, alumno=pago.alumno)


@bp.route("/<int:id_pago>/recibo.pdf")
def recibo_pdf(id_pago):
    pago = Pago.query.filter(Pago.eliminado_en.is_(None)).filter_by(id_pago=id_pago).first_or_404()
    config, logo = configuracion_y_logo()
    buffer = generar_recibo_pago(
        pago, pago.alumno, logo_path=logo, nombre_academia=config.nombre_academia,
        es_copia=request.args.get("copia") == "1",
    )
    nombre = f"recibo_{pago.id_pago:06d}_{pago.alumno.apellido}.pdf"
    return enviar_buffer(buffer, "recibos", nombre, "application/pdf")


@bp.route("/<int:id_pago>/eliminar", methods=["POST"])
def eliminar(id_pago):
    pago = Pago.query.filter(Pago.eliminado_en.is_(None)).filter_by(id_pago=id_pago).first_or_404()
    movimiento = MovimientoContable.query.filter_by(
        origen_tipo="Pago", origen_id=pago.id_pago
    ).first()
    try:
        motivo = texto_requerido(
            request.form.get("motivo"), "Motivo de anulación", 255
        )
    except ErrorValidacion as error:
        flash(str(error), "danger")
        return redirect(url_for("alumnos.detalle", id_alumno=pago.id_alumno))
    id_alumno = pago.id_alumno
    alumno_nombre = pago.alumno.nombre_completo if pago.alumno else f"Alumno #{pago.id_alumno}"
    alumno_codigo = pago.alumno.codigo_interno if pago.alumno else ""
    monto_pago = float(pago.monto)
    mes_pagado = pago.mes_pagado
    modo_pago = pago.modo_pago
    numero_recibo = f"{pago.id_pago:06d}"

    pago.eliminado_en = ahora_utc()
    if movimiento:
        movimiento.anulado_en = pago.eliminado_en
        movimiento.motivo_anulacion = f"Pago #{numero_recibo} anulado: {motivo}"
    db.session.add(AnulacionPago(
        id_pago=pago.id_pago, motivo=motivo, creado_en=pago.eliminado_en
    ))
    db.session.add(Auditoria(
        modulo="Pagos",
        accion="Anular",
        entidad="Pago",
        id_entidad=pago.id_pago,
        id_usuario=session.get("id_usuario"),
        valor_anterior=f"Recibo #{numero_recibo} | {alumno_nombre} ({alumno_codigo}) | Mes: {mes_pagado} | Bs. {monto_pago:.2f} ({modo_pago})",
        valor_nuevo=f"ANULADO | Motivo: {motivo}",
        detalle=f"Se anuló el Recibo #{numero_recibo} de {alumno_nombre} (Mes: {mes_pagado}, Bs. {monto_pago:.2f}, {modo_pago}). Motivo: {motivo}",
    ))
    db.session.commit()
    flash(f"Pago #{numero_recibo} de {alumno_nombre} anulado formalmente. El mes {mes_pagado} queda disponible para corrección.", "success")
    return redirect(request.referrer or url_for("alumnos.detalle", id_alumno=id_alumno))


@bp.route("/alumno/<int:id_alumno>/fecha-base", methods=["POST"])
def cambiar_fecha_base(id_alumno):
    alumno = Alumno.query.get_or_404(id_alumno)
    if alumno.estado == "Retirado":
        flash(
            "No se puede modificar la fecha de pago de un alumno retirado. "
            "Cámbielo a Activo para continuar.",
            "warning",
        )
        return redirect(url_for("alumnos.detalle", id_alumno=id_alumno))

    try:
        motivo = texto_requerido(
            request.form.get("motivo"), "Motivo del cambio", 255
        )
        nueva_fecha = fecha_no_futura(
            fecha_iso(request.form.get("fecha_base_pago"), "Fecha base"),
            "Fecha base",
        )
    except ErrorValidacion as error:
        flash(str(error), "danger")
        return redirect(url_for("alumnos.detalle", id_alumno=id_alumno))

    fecha_anterior = alumno.fecha_base_pago
    respaldo = crear_respaldo(current_app, "antes_recalcular_vencimientos")
    alumno.fecha_base_pago = nueva_fecha
    consulta_pagos = Pago.query.filter_by(id_alumno=id_alumno, eliminado_en=None)
    if alumno.fecha_ultima_reactivacion:
        consulta_pagos = consulta_pagos.filter(
            Pago.mes_pagado >= alumno.fecha_ultima_reactivacion.strftime("%Y-%m")
        )
    pagos = consulta_pagos.all()
    vencimientos_anteriores = "; ".join(
        f"{pago.id_pago}:{pago.fecha_vencimiento.isoformat()}" for pago in pagos
    )
    for pago in pagos:
        pago.fecha_vencimiento = calcular_vencimiento(
            alumno, pago.fecha_pago, pago.mes_pagado
        )
    db.session.add(HistorialAlumno(
        id_alumno=id_alumno, tipo="fecha_base_pago",
        valor_anterior=fecha_anterior.isoformat() if fecha_anterior else None,
        valor_nuevo=nueva_fecha.isoformat(),
        motivo=f"{motivo}. Vencimientos anteriores: {vencimientos_anteriores}"[:255],
    ))
    db.session.add(Auditoria(
        modulo="Pagos", accion="Recalcular vencimientos", entidad="Alumno",
        id_entidad=id_alumno,
        detalle=f"{fecha_anterior} -> {nueva_fecha}; respaldo={respaldo}",
    ))
    db.session.commit()
    flash(
        "Fecha base actualizada y vencimientos activos recalculados correctamente.",
        "success",
    )
    return redirect(url_for("alumnos.detalle", id_alumno=id_alumno))


@bp.route("/exportar")
def exportar():
    """Exporta a Excel los pagos que coincidan con TODOS los filtros activos
    en el listado (nombre, apellido, categoría, edad, beca, sexo, estado,
    fecha de pago/vencimiento, mes de vencimiento). Si no se aplica ningún
    filtro, exporta el historial completo."""
    pagos = _filtrar_pagos(request.args)
    encabezados, filas = _datos_exportacion_pagos(pagos)
    titulo, nombre_base = _nombre_exportacion("Registro de pagos")
    _, logo_configurado = configuracion_y_logo()
    logo_path = logo_configurado if request.args.get("incluir_escudo") else None
    buffer = exportar_tabla_excel(titulo, encabezados, filas, logo_path=logo_path)
    nombre = f"{nombre_base}.xlsx"
    return enviar_buffer(
        buffer, "reportes_pagos", nombre,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/exportar.pdf")
def exportar_pdf():
    pagos = _filtrar_pagos(request.args)
    encabezados, filas = _datos_exportacion_pagos(pagos)
    titulo, nombre_base = _nombre_exportacion("Registro de pagos")
    _, logo_configurado = configuracion_y_logo()
    logo_path = logo_configurado if request.args.get("incluir_escudo") else None
    buffer = generar_tabla_pdf(
        titulo, encabezados, filas, orientacion="vertical",
        tamano_pagina="carta", tamano_letra=12, logo_path=logo_path,
    )
    nombre = f"{nombre_base}.pdf"
    return enviar_buffer(buffer, "reportes_pagos", nombre, "application/pdf")


@bp.route("/resumen-6-meses.xlsx")
def resumen_seis_meses_excel():
    encabezados, filas, meses = _datos_resumen_seis_meses(request.args)
    titulo_predeterminado = f"Resumen de pagos {MESES_ES[meses[0].month - 1]} - {MESES_ES[meses[-1].month - 1]} {meses[-1].year}"
    titulo, nombre_base = _nombre_exportacion(titulo_predeterminado)
    _, logo_configurado = configuracion_y_logo()
    logo_path = logo_configurado if request.args.get("incluir_escudo") else None
    buffer = exportar_tabla_excel(
        titulo, encabezados, filas, logo_path=logo_path, orientacion="horizontal"
    )
    return enviar_buffer(
        buffer, "reportes_pagos", f"{nombre_base}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/resumen-6-meses.pdf")
def resumen_seis_meses_pdf():
    encabezados, filas, meses = _datos_resumen_seis_meses(request.args)
    titulo_predeterminado = f"Resumen de pagos {MESES_ES[meses[0].month - 1]} - {MESES_ES[meses[-1].month - 1]} {meses[-1].year}"
    titulo, nombre_base = _nombre_exportacion(titulo_predeterminado)
    _, logo_configurado = configuracion_y_logo()
    logo_path = logo_configurado if request.args.get("incluir_escudo") else None
    buffer = generar_tabla_pdf(
        titulo, encabezados, filas, orientacion="horizontal",
        tamano_pagina="carta", tamano_letra=9, logo_path=logo_path,
    )
    return enviar_buffer(
        buffer, "reportes_pagos", f"{nombre_base}.pdf", "application/pdf"
    )


@bp.route("/exportar-form")
def exportar_form():
    return render_template("pagos/exportar.html")
