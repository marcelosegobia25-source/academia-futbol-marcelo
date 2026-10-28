from datetime import date, timedelta
from calendar import monthrange
from decimal import Decimal, InvalidOperation
import csv
import io
import os
import uuid

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for, Response, send_file, session
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    Alumno, Auditoria, CategoriaContable, Compra, CuotaProgramada, DetalleCompra, DetalleVenta, MODOS_MOVIMIENTO, MovimientoContable,
    MovimientoInventario, PagoProgramado, Producto, ProductoVariante, Proveedor, Venta,
    ahora_utc, SesionCaja, CierreCaja, ConteoInventario, DetalleConteoInventario,
    DevolucionVenta, DetalleDevolucionVenta,
)
from app.utils.excel import exportar_tabla_excel
from app.utils.pdf_tablas import generar_tabla_pdf
from app.utils.personalizacion import configuracion_y_logo
from app.utils.validacion import ErrorValidacion, solo_numeros_opcional



bp = Blueprint("gestion", __name__, url_prefix="/gestion")


def _exigir_caja_abierta():
    if not current_app.config.get("AUTH_REQUIRED", True):
        return None
    abierta = SesionCaja.query.filter(
        SesionCaja.id_usuario == session.get("id_usuario"),
        SesionCaja.estado.in_(("Abierta", "Reabierta")),
    ).first()
    if abierta:
        return None
    flash("Debe abrir su caja antes de registrar una operación financiera.", "warning")
    return redirect(url_for("pagos.caja"))


@bp.before_request
def validar_sesion_financiera():
    if request.method == "POST" and request.endpoint in {
        "gestion.movimiento_nuevo", "gestion.cuota_programada_pagar", "gestion.venta_nueva",
        "gestion.venta_devolver", "gestion.compra_nueva"
    }:
        return _exigir_caja_abierta()


def _decimal(valor, campo, minimo=Decimal("0")):
    try:
        numero = Decimal(str(valor or "0"))
    except InvalidOperation as error:
        raise ValueError(f"{campo} no es válido.") from error
    if numero < minimo:
        raise ValueError(f"{campo} debe ser mayor o igual a {minimo}.")
    return numero.quantize(Decimal("0.01"))


def _entero(valor, campo, minimo=0):
    try:
        numero = int(valor)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{campo} no es válido.") from error
    if numero < minimo:
        raise ValueError(f"{campo} debe ser mayor o igual a {minimo}.")
    return numero


def _fecha(valor):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError) as error:
        raise ValueError("La fecha no es válida.") from error


def _consulta_contable():
    consulta = MovimientoContable.query
    tipo = request.args.get("tipo", "")
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    categoria = request.args.get("categoria", "").strip()
    if tipo in {"Ingreso", "Egreso"}:
        consulta = consulta.filter_by(tipo=tipo)
    if desde:
        try:
            consulta = consulta.filter(MovimientoContable.fecha >= _fecha(desde))
        except ValueError:
            pass
    if hasta:
        try:
            consulta = consulta.filter(MovimientoContable.fecha <= _fecha(hasta))
        except ValueError:
            pass
    if categoria:
        consulta = consulta.filter(MovimientoContable.categoria == categoria)
    return consulta.order_by(MovimientoContable.fecha.desc(), MovimientoContable.id_movimiento.desc())


def _filas_contables(movimientos):
    return [[m.fecha.strftime("%d/%m/%Y"), m.tipo, m.categoria, m.concepto,
             m.modo_pago, f"{m.monto:.2f}", "Activo" if m.activo else "Anulado"]
            for m in movimientos]


def _guardar_comprobante(archivo):
    if not archivo or not archivo.filename:
        return None
    seguro = secure_filename(archivo.filename)
    if "." not in seguro:
        raise ValueError("El comprobante no tiene una extensión válida.")
    extension = seguro.rsplit(".", 1)[1].lower()
    if extension not in current_app.config["ALLOWED_DOCUMENT_EXT"]:
        raise ValueError("El comprobante debe ser PDF, PNG, JPG, JPEG o WEBP.")
    nombre = f"comprobante_{uuid.uuid4().hex}.{extension}"
    archivo.save(os.path.join(current_app.config["DOCUMENT_FOLDER"], nombre))
    return nombre


def _fecha_mensual(referencia, dia_mes, avanzar=False):
    año, mes = referencia.year, referencia.month
    if avanzar:
        mes += 1
        if mes == 13:
            año, mes = año + 1, 1
    dia = min(dia_mes, monthrange(año, mes)[1])
    candidata = date(año, mes, dia)
    if not avanzar and candidata < referencia:
        return _fecha_mensual(referencia, dia_mes, avanzar=True)
    return candidata


def _siguiente_fecha(programado, actual):
    if programado.frecuencia == "Dias":
        return actual + timedelta(days=programado.intervalo_dias)
    return _fecha_mensual(actual, programado.dia_mes, avanzar=True)


def _generar_cuotas(programado, hasta):
    if not programado.activo or not programado.proxima_fecha:
        return 0
    creadas = 0
    fecha_cuota = programado.proxima_fecha
    while fecha_cuota <= hasta and (not programado.fecha_fin or fecha_cuota <= programado.fecha_fin):
        existe = CuotaProgramada.query.filter_by(
            id_programado=programado.id_programado,
            fecha_vencimiento=fecha_cuota,
        ).first()
        if not existe:
            db.session.add(CuotaProgramada(
                programado=programado, fecha_vencimiento=fecha_cuota,
                monto=programado.monto,
            ))
            creadas += 1
        fecha_cuota = _siguiente_fecha(programado, fecha_cuota)
    programado.proxima_fecha = None if programado.fecha_fin and fecha_cuota > programado.fecha_fin else fecha_cuota
    return creadas


def generar_calendario_programado(hasta=None):
    """Extiende de forma idempotente el calendario al iniciar el sistema."""
    hasta = hasta or date.today() + timedelta(days=366)
    creadas = sum(
        _generar_cuotas(programado, hasta)
        for programado in PagoProgramado.query.filter_by(activo=True).all()
    )
    db.session.commit()
    return creadas


@bp.route("/contabilidad")
def contabilidad():
    consulta = _consulta_contable()
    pagina = consulta.paginate(
        page=max(1, request.args.get("page", 1, type=int)),
        per_page=50, error_out=False,
    )
    movimientos = pagina.items
    mes_resumen = request.args.get("mes_resumen", "").strip()
    try:
        inicio_mes = date.fromisoformat(f"{mes_resumen}-01") if mes_resumen else date.today().replace(day=1)
    except ValueError:
        inicio_mes = date.today().replace(day=1)
    fin_mes = _fecha_mensual(inicio_mes, 1, avanzar=True) - timedelta(days=1)
    mes_resumen = inicio_mes.strftime("%Y-%m")

    resumen_mensual = MovimientoContable.query.filter(
        MovimientoContable.fecha >= inicio_mes,
        MovimientoContable.fecha <= fin_mes,
    ).with_entities(
        MovimientoContable.tipo, MovimientoContable.monto, MovimientoContable.anulado_en
    ).all()
    ingresos = sum((Decimal(monto) for tipo, monto, anulado in resumen_mensual if tipo == "Ingreso" and anulado is None), Decimal("0"))
    egresos = sum((Decimal(monto) for tipo, monto, anulado in resumen_mensual if tipo == "Egreso" and anulado is None), Decimal("0"))
    resumen_acumulado = MovimientoContable.query.with_entities(
        MovimientoContable.tipo, MovimientoContable.monto, MovimientoContable.anulado_en
    ).all()
    ingresos_acumulados = sum((Decimal(monto) for tipo, monto, anulado in resumen_acumulado if tipo == "Ingreso" and anulado is None), Decimal("0"))
    egresos_acumulados = sum((Decimal(monto) for tipo, monto, anulado in resumen_acumulado if tipo == "Egreso" and anulado is None), Decimal("0"))
    recientes_base = MovimientoContable.query.filter(
        MovimientoContable.fecha >= inicio_mes,
        MovimientoContable.fecha <= fin_mes,
        MovimientoContable.anulado_en.is_(None),
    )
    ingresos_recientes = recientes_base.filter_by(tipo="Ingreso").order_by(
        MovimientoContable.fecha.desc(), MovimientoContable.id_movimiento.desc()
    ).limit(5).all()
    egresos_recientes = recientes_base.filter_by(tipo="Egreso").order_by(
        MovimientoContable.fecha.desc(), MovimientoContable.id_movimiento.desc()
    ).limit(5).all()
    categorias_resumen = []
    for tipo in ("Ingreso", "Egreso"):
        nombres = db.session.query(MovimientoContable.categoria).filter(
            MovimientoContable.tipo == tipo,
            MovimientoContable.fecha >= inicio_mes,
            MovimientoContable.fecha <= fin_mes,
            MovimientoContable.anulado_en.is_(None),
        ).distinct().order_by(MovimientoContable.categoria).all()
        for (nombre,) in nombres:
            items = recientes_base.filter_by(tipo=tipo, categoria=nombre).order_by(
                MovimientoContable.fecha.desc(), MovimientoContable.id_movimiento.desc()
            ).all()
            categorias_resumen.append({
                "tipo": tipo, "nombre": nombre, "movimientos": items[:5],
                "cantidad": len(items),
                "total": sum((Decimal(item.monto) for item in items), Decimal("0")),
            })
    categorias = [fila[0] for fila in db.session.query(MovimientoContable.categoria).distinct().order_by(MovimientoContable.categoria)]
    return render_template(
        "gestion/contabilidad.html", movimientos=movimientos, ingresos=ingresos,
        egresos=egresos, saldo=ingresos-egresos, categorias=categorias,
        saldo_acumulado=ingresos_acumulados-egresos_acumulados,
        mes_resumen=mes_resumen, inicio_mes=inicio_mes, fin_mes=fin_mes,
        ingresos_recientes=ingresos_recientes, egresos_recientes=egresos_recientes,
        categorias_resumen=categorias_resumen,
        vista_movimientos=request.args.get("vista") == "movimientos",
        filtros=request.args, pagina=pagina,
    )


@bp.route("/contabilidad/nuevo", methods=["GET", "POST"])
def movimiento_nuevo():
    proveedores = Proveedor.query.filter_by(activo=True).order_by(Proveedor.nombre).all()
    categorias_contables = CategoriaContable.query.filter_by(activo=True).order_by(CategoriaContable.tipo, CategoriaContable.nombre).all()
    archivo_guardado = None
    if request.method == "POST":
        try:
            tipo = request.form.get("tipo")
            if tipo not in {"Ingreso", "Egreso"}:
                raise ValueError("Seleccione ingreso o egreso.")
            concepto = request.form.get("concepto", "").strip()
            categoria = request.form.get("categoria", "").strip()
            categoria_obj = CategoriaContable.query.filter_by(nombre=categoria, activo=True).first()
            if not categoria_obj and categoria:
                categoria_obj = CategoriaContable(nombre=categoria[:80], tipo=tipo)
                db.session.add(categoria_obj)
                db.session.flush()
            if not concepto or not categoria:
                raise ValueError("Concepto y categoría son obligatorios.")
            modo = request.form.get("modo_pago", "Efectivo")
            if not categoria_obj or categoria_obj.tipo not in {tipo, "Ambos"}:
                raise ValueError("La categoría contable no corresponde al tipo de movimiento.")
            if modo not in MODOS_MOVIMIENTO:
                raise ValueError("El método de pago no es válido.")
            id_proveedor = request.form.get("id_proveedor", type=int)
            if id_proveedor and not db.session.get(Proveedor, id_proveedor):
                raise ValueError("El proveedor seleccionado no existe.")
            archivo_guardado = _guardar_comprobante(request.files.get("comprobante"))
            movimiento = MovimientoContable(
                tipo=tipo, categoria=categoria[:80], id_categoria_contable=categoria_obj.id_categoria_contable,
                concepto=concepto[:180],
                monto=_decimal(request.form.get("monto"), "Monto", Decimal("0.01")),
                fecha=_fecha(request.form.get("fecha")), modo_pago=modo,
                numero_operacion=request.form.get("numero_operacion", "").strip() or None,
                id_proveedor=id_proveedor,
                observacion=request.form.get("observacion", "").strip() or None,
                comprobante=archivo_guardado,
            )
            db.session.add(movimiento)
            db.session.flush()
            db.session.add(Auditoria(
                modulo="Contabilidad", accion="Registrar", entidad="MovimientoContable",
                id_entidad=movimiento.id_movimiento,
                detalle=f"{tipo}: {concepto} - {movimiento.monto}",
            ))
            db.session.commit()
            flash("Movimiento contable registrado.", "success")
            return redirect(url_for("gestion.contabilidad"))
        except ValueError as error:
            if archivo_guardado:
                os.remove(os.path.join(current_app.config["DOCUMENT_FOLDER"], archivo_guardado))
            flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback()
            if archivo_guardado:
                os.remove(os.path.join(current_app.config["DOCUMENT_FOLDER"], archivo_guardado))
            current_app.logger.exception("No se pudo registrar el movimiento contable")
            flash("No se pudo registrar el movimiento. Revise los datos e intente nuevamente.", "danger")
    return render_template(
        "gestion/movimiento_form.html", modos=MODOS_MOVIMIENTO,
        proveedores=proveedores, categorias_contables=categorias_contables, hoy=date.today().isoformat(),
    )


@bp.route("/contabilidad/categorias", methods=["GET", "POST"])
def categorias_contables():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        tipo = request.form.get("tipo", "Ambos")
        volver = request.form.get("volver", "").strip()
        if not nombre or tipo not in {"Ingreso", "Egreso", "Ambos"}:
            flash("Nombre y tipo de categoría son obligatorios.", "danger")
        elif CategoriaContable.query.filter(db.func.lower(CategoriaContable.nombre) == nombre.lower()).first():
            flash("Esa categoría ya existe.", "warning")
        else:
            db.session.add(CategoriaContable(nombre=nombre[:80], tipo=tipo))
            db.session.commit()
            flash("Categoría contable creada.", "success")
            if volver == "pago_programado_nuevo":
                return redirect(url_for("gestion.pago_programado_nuevo"))
            return redirect(url_for("gestion.categorias_contables"))
    categorias = CategoriaContable.query.order_by(CategoriaContable.tipo, CategoriaContable.nombre).all()
    return render_template(
        "gestion/categorias_contables.html", categorias=categorias,
        tipo_inicial=request.args.get("tipo", "Ambos"), volver=request.args.get("volver", ""),
    )


@bp.route("/contabilidad/categorias/<int:id_categoria>/tipo", methods=["POST"])
def categoria_contable_tipo(id_categoria):
    categoria = CategoriaContable.query.get_or_404(id_categoria)
    nombre = request.form.get("nombre", "").strip()
    tipo = request.form.get("tipo")
    repetida = CategoriaContable.query.filter(
        db.func.lower(CategoriaContable.nombre) == nombre.lower(),
        CategoriaContable.id_categoria_contable != categoria.id_categoria_contable,
    ).first() if nombre else None
    if not nombre or tipo not in {"Ingreso", "Egreso", "Ambos"}:
        flash("El nombre y tipo de categoría son obligatorios.", "danger")
    elif repetida:
        flash("Ya existe otra categoría con ese nombre.", "warning")
    else:
        nombre_anterior = categoria.nombre
        nombre = nombre[:80]
        incompatibles = MovimientoContable.query.filter(
            MovimientoContable.id_categoria_contable == categoria.id_categoria_contable,
            MovimientoContable.tipo != tipo,
        ).count() if tipo != "Ambos" else 0
        if incompatibles:
            flash("No se puede cambiar el tipo: existen movimientos históricos incompatibles.", "danger")
            return redirect(url_for("gestion.categorias_contables"))
        categoria.nombre = nombre
        categoria.tipo = tipo
        db.session.commit()
        flash("Categoría actualizada en todos sus movimientos y pagos programados.", "success")
    return redirect(url_for("gestion.categorias_contables"))


@bp.route("/contabilidad/<int:id_movimiento>/comprobante")
def movimiento_comprobante(id_movimiento):
    movimiento = MovimientoContable.query.get_or_404(id_movimiento)
    if not movimiento.comprobante:
        abort(404)
    ruta = os.path.join(current_app.config["DOCUMENT_FOLDER"], movimiento.comprobante)
    if not os.path.isfile(ruta):
        abort(404)
    return send_file(ruta, as_attachment=True, download_name=movimiento.comprobante)


@bp.route("/contabilidad/<int:id_movimiento>/anular", methods=["POST"])
def movimiento_anular(id_movimiento):
    movimiento = MovimientoContable.query.get_or_404(id_movimiento)
    if not movimiento.activo:
        flash("El movimiento ya está anulado.", "warning")
    elif movimiento.origen_tipo in {"Pago", "Venta"}:
        flash("Debe anularse desde el módulo que originó el movimiento.", "danger")
    elif movimiento.sesion_caja and movimiento.sesion_caja.estado == "Cerrada":
        flash("No puede anular un movimiento perteneciente a una caja cerrada.", "danger")
    elif CierreCaja.query.filter_by(fecha=movimiento.fecha, reabierto_en=None).first():
        flash("No se puede anular un movimiento de una fecha con caja cerrada. Reabra primero ese cierre.", "danger")
    else:
        motivo = request.form.get("motivo", "").strip()
        if not motivo:
            flash("El motivo es obligatorio.", "danger")
            return redirect(url_for("gestion.contabilidad"))
        movimiento.anulado_en = ahora_utc()
        movimiento.motivo_anulacion = motivo[:255]
        db.session.add(Auditoria(
            modulo="Contabilidad", accion="Anular", entidad="MovimientoContable",
            id_entidad=movimiento.id_movimiento, detalle=motivo,
        ))
        db.session.commit()
        flash("Movimiento anulado.", "success")
    return redirect(url_for("gestion.contabilidad"))


@bp.route("/contabilidad/exportar.csv")
def contabilidad_csv():
    movimientos = _consulta_contable().all()
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(["Fecha", "Tipo", "Categoría", "Concepto", "Monto", "Método", "Estado"])
    for m in movimientos:
        escritor.writerow([m.fecha.isoformat(), m.tipo, m.categoria, m.concepto, m.monto, m.modo_pago, "Activo" if m.activo else "Anulado"])
    return Response(
        "\ufeff" + salida.getvalue(), mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=contabilidad.csv"},
    )


@bp.route("/contabilidad/exportar.pdf")
def contabilidad_pdf():
    movimientos = _consulta_contable().all()
    encabezados, filas = _campos_reporte("contabilidad", _filas_contables(movimientos))
    _, logo = configuracion_y_logo()
    archivo = generar_tabla_pdf("Contabilidad", encabezados, filas, logo_path=logo)
    return send_file(archivo, mimetype="application/pdf", as_attachment=True, download_name="contabilidad.pdf")


@bp.route("/contabilidad/exportar.xlsx")
def contabilidad_excel():
    movimientos = _consulta_contable().all()
    encabezados, filas = _campos_reporte("contabilidad", _filas_contables(movimientos))
    _, logo = configuracion_y_logo()
    archivo = exportar_tabla_excel("Contabilidad", encabezados, filas, logo_path=logo)
    return send_file(archivo, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="contabilidad.xlsx")


def _enviar_reporte_gestion(titulo, encabezados, filas, nombre, formato):
    _, logo = configuracion_y_logo()
    if formato == "pdf":
        archivo = generar_tabla_pdf(titulo, encabezados, filas, logo_path=logo)
        return send_file(archivo, mimetype="application/pdf", as_attachment=True, download_name=f"{nombre}.pdf")
    archivo = exportar_tabla_excel(titulo, encabezados, filas, logo_path=logo)
    return send_file(archivo, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=f"{nombre}.xlsx")


REPORTES_GESTION = {
    "contabilidad": [("fecha", "Fecha"), ("tipo", "Tipo"), ("categoria", "Categoría"), ("concepto", "Concepto"), ("metodo", "Método"), ("monto", "Monto"), ("estado", "Estado")],
    "pagos-programados": [("vencimiento", "Vencimiento"), ("concepto", "Concepto"), ("categoria", "Categoría"), ("proveedor", "Proveedor"), ("monto", "Monto"), ("estado", "Estado"), ("fecha_pago", "Fecha de pago")],
    "compras": [("numero", "N.º"), ("fecha", "Fecha"), ("proveedor", "Proveedor"), ("factura", "Factura"), ("productos", "Productos"), ("metodo", "Método"), ("total", "Total"), ("estado", "Estado")],
    "inventario": [("codigo", "Código"), ("producto", "Producto"), ("categoria", "Categoría"), ("talla", "Talla"), ("color", "Color"), ("compra", "Compra"), ("venta", "Venta"), ("stock", "Stock"), ("minimo", "Mínimo"), ("estado", "Estado")],
    "ventas": [("numero", "N.º"), ("fecha", "Fecha"), ("cliente", "Cliente"), ("productos", "Productos"), ("metodo", "Método"), ("subtotal", "Subtotal"), ("descuento", "Descuento"), ("total", "Total"), ("estado", "Estado")],
}


def _campos_reporte(modulo, valores):
    definiciones = REPORTES_GESTION[modulo]
    seleccionadas = request.args.getlist("columnas")
    disponibles = {clave: (indice, etiqueta) for indice, (clave, etiqueta) in enumerate(definiciones)}
    if not seleccionadas or any(clave not in disponibles for clave in seleccionadas):
        abort(400, description="Seleccione al menos una columna válida para exportar.")
    indices = [disponibles[clave][0] for clave in seleccionadas]
    return [disponibles[clave][1] for clave in seleccionadas], [[fila[i] for i in indices] for fila in valores]


@bp.route("/reportes/<modulo>")
def reporte_exportar_form(modulo):
    if modulo not in REPORTES_GESTION:
        abort(404)
    rutas = {
        "contabilidad": (url_for("gestion.contabilidad_excel"), url_for("gestion.contabilidad_pdf")),
        "pagos-programados": (
            url_for("gestion.pagos_programados_exportar", formato="xlsx"),
            url_for("gestion.pagos_programados_exportar", formato="pdf"),
        ),
        "compras": (url_for("gestion.compras_exportar", formato="xlsx"), url_for("gestion.compras_exportar", formato="pdf")),
        "inventario": (url_for("gestion.inventario_exportar", formato="xlsx"), url_for("gestion.inventario_exportar", formato="pdf")),
        "ventas": (url_for("gestion.ventas_exportar", formato="xlsx"), url_for("gestion.ventas_exportar", formato="pdf")),
    }
    ruta_excel, ruta_pdf = rutas[modulo]
    return render_template(
        "gestion/exportar_reporte.html", modulo=modulo,
        columnas=REPORTES_GESTION[modulo], ruta_excel=ruta_excel, ruta_pdf=ruta_pdf,
    )


@bp.route("/pagos-programados/exportar.<formato>")
def pagos_programados_exportar(formato):
    if formato not in {"pdf", "xlsx"}:
        return "Formato no válido", 404
    estado = request.args.get("estado", "Pendiente")
    consulta = CuotaProgramada.query
    if estado in {"Pendiente", "Pagado", "Omitido"}:
        consulta = consulta.filter_by(estado=estado)
    if estado in {"Pendiente", "Pagado", "Omitido"}:
        inicio_periodo, fin_periodo, _ = _periodo_pagos_programados(request.args.get("periodo"))
        consulta = consulta.filter(CuotaProgramada.fecha_vencimiento.between(inicio_periodo, fin_periodo))
    cuotas = consulta.order_by(CuotaProgramada.fecha_vencimiento, CuotaProgramada.id_cuota).all()
    valores = [[cuota.fecha_vencimiento.strftime("%d/%m/%Y"), cuota.programado.concepto,
              cuota.programado.categoria, cuota.programado.proveedor.nombre if cuota.programado.proveedor else "—",
              f"{cuota.monto:.2f}", cuota.estado,
              cuota.fecha_pago.strftime("%d/%m/%Y") if cuota.fecha_pago else "—"] for cuota in cuotas]
    encabezados, filas = _campos_reporte("pagos-programados", valores)
    return _enviar_reporte_gestion("Pagos programados", encabezados, filas, "pagos_programados", formato)


@bp.route("/pagos-programados")
def pagos_programados():
    estado = request.args.get("estado", "Pendiente")
    hoy = date.today()
    inicio_periodo, fin_periodo, periodo = _periodo_pagos_programados(request.args.get("periodo"))
    consulta = CuotaProgramada.query
    if estado in {"Pendiente", "Pagado", "Omitido"}:
        consulta = consulta.filter_by(estado=estado)
    if estado in {"Pendiente", "Pagado", "Omitido"}:
        consulta = consulta.filter(CuotaProgramada.fecha_vencimiento.between(inicio_periodo, fin_periodo))
    cuotas = consulta.order_by(CuotaProgramada.fecha_vencimiento, CuotaProgramada.id_cuota).all()
    programados = PagoProgramado.query.order_by(PagoProgramado.activo.desc(), PagoProgramado.concepto).all()
    pendientes = CuotaProgramada.query.filter(
        CuotaProgramada.estado == "Pendiente",
        CuotaProgramada.fecha_vencimiento.between(inicio_periodo, fin_periodo),
    ).all()
    return render_template(
        "gestion/pagos_programados.html", programados=programados, cuotas=cuotas,
        estado=estado, hoy=hoy, periodo=periodo,
        vencidos=sum(1 for cuota in pendientes if cuota.fecha_vencimiento < hoy),
        proximos=sum(1 for cuota in pendientes if cuota.fecha_vencimiento >= hoy),
        total_pendiente=sum((Decimal(cuota.monto) for cuota in pendientes), Decimal("0")),
        modos=MODOS_MOVIMIENTO,
    )


def _periodo_pagos_programados(valor):
    hoy = date.today()
    try:
        anio_texto, mes_texto = (valor or hoy.strftime("%Y-%m")).split("-", 1)
        anio, mes = int(anio_texto), int(mes_texto)
        if not 2000 <= anio <= 2100 or not 1 <= mes <= 12:
            raise ValueError
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month
    inicio = date(anio, mes, 1)
    fin = date(anio, mes, monthrange(anio, mes)[1])
    return inicio, fin, f"{anio:04d}-{mes:02d}"


@bp.route("/pagos-programados/nuevo", methods=["GET", "POST"])
def pago_programado_nuevo():
    proveedores = Proveedor.query.filter_by(activo=True).order_by(Proveedor.nombre).all()
    categorias_contables = CategoriaContable.query.filter_by(activo=True).order_by(CategoriaContable.nombre).all()
    if request.method == "POST":
        try:
            concepto = request.form.get("concepto", "").strip()
            categoria = request.form.get("categoria", "").strip()
            categoria_obj = CategoriaContable.query.filter_by(nombre=categoria, activo=True).first()
            if not categoria_obj and categoria:
                categoria_obj = CategoriaContable(nombre=categoria[:80], tipo="Egreso")
                db.session.add(categoria_obj)
                db.session.flush()
            if not concepto or not categoria:
                raise ValueError("Concepto y categoría son obligatorios.")
            frecuencia = request.form.get("frecuencia")
            if not categoria_obj or categoria_obj.tipo not in {"Egreso", "Ambos"}:
                raise ValueError("Seleccione una categoría válida de egreso.")
            if frecuencia not in {"Dias", "Mensual"}:
                raise ValueError("Seleccione una frecuencia válida.")
            intervalo = _entero(request.form.get("intervalo_dias"), "Intervalo", 1) if frecuencia == "Dias" else None
            dia_mes = _entero(request.form.get("dia_mes"), "Día del mes", 1) if frecuencia == "Mensual" else None
            if dia_mes and dia_mes > 31:
                raise ValueError("El día mensual debe estar entre 1 y 31.")
            inicio = _fecha(request.form.get("fecha_inicio"))
            fin_texto = request.form.get("fecha_fin", "").strip()
            fin = _fecha(fin_texto) if fin_texto else None
            if fin and fin < inicio:
                raise ValueError("La fecha final no puede ser anterior al inicio.")
            modo = request.form.get("modo_pago", "Efectivo")
            if modo not in MODOS_MOVIMIENTO:
                raise ValueError("El método de pago no es válido.")
            id_proveedor = request.form.get("id_proveedor", type=int)
            if id_proveedor and not db.session.get(Proveedor, id_proveedor):
                raise ValueError("El proveedor seleccionado no existe.")
            primera = inicio if frecuencia == "Dias" else _fecha_mensual(inicio, dia_mes)
            programado = PagoProgramado(
                concepto=concepto[:180], categoria=categoria[:80],
                id_categoria_contable=categoria_obj.id_categoria_contable,
                monto=_decimal(request.form.get("monto"), "Monto", Decimal("0.01")),
                id_proveedor=id_proveedor, modo_pago=modo, frecuencia=frecuencia,
                intervalo_dias=intervalo, dia_mes=dia_mes, fecha_inicio=inicio,
                fecha_fin=fin, proxima_fecha=primera,
                observacion=request.form.get("observacion", "").strip()[:255] or None,
            )
            db.session.add(programado)
            db.session.flush()
            creadas = _generar_cuotas(programado, min(fin, inicio + timedelta(days=366)) if fin else inicio + timedelta(days=366))
            db.session.add(Auditoria(
                modulo="Pagos programados", accion="Crear", entidad="PagoProgramado",
                id_entidad=programado.id_programado, detalle=f"{concepto}; {creadas} cuotas",
            ))
            db.session.commit()
            flash(f"Pago programado creado con {creadas} cuota(s).", "success")
            return redirect(url_for("gestion.pagos_programados"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("No se pudo crear el pago programado")
            flash("No se pudo crear el pago programado.", "danger")
    return render_template(
        "gestion/pago_programado_form.html", proveedores=proveedores,
        categorias_contables=categorias_contables, modos=MODOS_MOVIMIENTO, hoy=date.today().isoformat(),
    )


@bp.route("/pagos-programados/generar", methods=["POST"])
def pagos_programados_generar():
    creadas = generar_calendario_programado()
    flash(f"Calendario actualizado: {creadas} cuota(s) nueva(s).", "success")
    return redirect(url_for("gestion.pagos_programados"))


@bp.route("/pagos-programados/<int:id_programado>/editar", methods=["GET", "POST"])
def pago_programado_editar(id_programado):
    programado = PagoProgramado.query.get_or_404(id_programado)
    proveedores = Proveedor.query.filter_by(activo=True).order_by(Proveedor.nombre).all()
    categorias_contables = CategoriaContable.query.filter_by(activo=True).order_by(CategoriaContable.nombre).all()
    if request.method == "POST":
        try:
            categoria = CategoriaContable.query.filter_by(
                nombre=request.form.get("categoria", "").strip(), activo=True
            ).first()
            if not categoria or categoria.tipo not in {"Egreso", "Ambos"}:
                raise ValueError("Seleccione una categoría válida de egreso.")
            monto = _decimal(request.form.get("monto"), "Monto", Decimal("0.01"))
            concepto = request.form.get("concepto", "").strip()
            if not concepto:
                raise ValueError("El concepto es obligatorio.")
            anterior = f"{programado.concepto}; {programado.monto}; {programado.categoria}"
            programado.concepto, programado.monto = concepto[:180], monto
            programado.categoria = categoria.nombre
            programado.id_categoria_contable = categoria.id_categoria_contable
            programado.id_proveedor = request.form.get("id_proveedor", type=int)
            programado.observacion = request.form.get("observacion", "").strip()[:255] or None
            # Solo se actualizan cuotas pendientes de hoy en adelante. Las
            # pagadas, omitidas y vencidas permanecen como evidencia histórica.
            CuotaProgramada.query.filter(
                CuotaProgramada.id_programado == id_programado,
                CuotaProgramada.estado == "Pendiente",
                CuotaProgramada.fecha_vencimiento >= date.today(),
            ).update({"monto": monto}, synchronize_session=False)
            db.session.add(Auditoria(
                modulo="Pagos programados", accion="Editar", entidad="PagoProgramado",
                id_entidad=id_programado, valor_anterior=anterior,
                valor_nuevo=f"{programado.concepto}; {monto}; {categoria.nombre}",
            ))
            db.session.commit()
            flash("Programación actualizada; el historial cerrado no fue modificado.", "success")
            return redirect(url_for("gestion.pagos_programados"))
        except ValueError as error:
            db.session.rollback(); flash(str(error), "danger")
    return render_template(
        "gestion/pago_programado_form.html", programado=programado,
        proveedores=proveedores, categorias_contables=categorias_contables,
        modos=MODOS_MOVIMIENTO, hoy=date.today().isoformat(),
    )


@bp.route("/pagos-programados/<int:id_programado>/estado", methods=["POST"])
def pago_programado_estado(id_programado):
    programado = PagoProgramado.query.get_or_404(id_programado)
    programado.activo = not programado.activo
    if programado.activo and not programado.proxima_fecha:
        ultima = CuotaProgramada.query.filter_by(id_programado=id_programado).order_by(CuotaProgramada.fecha_vencimiento.desc()).first()
        programado.proxima_fecha = _siguiente_fecha(programado, ultima.fecha_vencimiento) if ultima else programado.fecha_inicio
        _generar_cuotas(programado, date.today() + timedelta(days=366))
    db.session.add(Auditoria(modulo="Pagos programados", accion="Activar" if programado.activo else "Pausar", entidad="PagoProgramado", id_entidad=id_programado, detalle=programado.concepto))
    db.session.commit()
    flash("Estado de la programación actualizado.", "success")
    return redirect(url_for("gestion.pagos_programados"))


@bp.route("/pagos-programados/cuota/<int:id_cuota>/pagar", methods=["POST"])
def cuota_programada_pagar(id_cuota):
    cuota = CuotaProgramada.query.get_or_404(id_cuota)
    if cuota.estado != "Pendiente":
        flash("La cuota ya fue procesada.", "warning")
        return redirect(url_for("gestion.pagos_programados"))
    try:
        fecha_pago = _fecha(request.form.get("fecha_pago"))
        if fecha_pago > date.today():
            raise ValueError("La fecha de pago no puede ser futura.")
        modo = request.form.get("modo_pago", cuota.programado.modo_pago)
        if modo not in MODOS_MOVIMIENTO:
            raise ValueError("El método de pago no es válido.")
        movimiento = MovimientoContable(
            tipo="Egreso", categoria=cuota.programado.categoria,
            concepto=cuota.programado.concepto, monto=cuota.monto,
            fecha=fecha_pago, modo_pago=modo,
            id_proveedor=cuota.programado.id_proveedor,
            numero_operacion=request.form.get("numero_operacion", "").strip() or None,
            origen_tipo="CuotaProgramada", origen_id=cuota.id_cuota,
        )
        db.session.add(movimiento)
        db.session.flush()
        cuota.estado = "Pagado"
        cuota.fecha_pago = fecha_pago
        cuota.id_movimiento = movimiento.id_movimiento
        db.session.add(Auditoria(modulo="Pagos programados", accion="Pagar cuota", entidad="CuotaProgramada", id_entidad=cuota.id_cuota, detalle=f"{cuota.programado.concepto}; {cuota.monto}"))
        db.session.commit()
        flash("Cuota pagada y egreso contable registrado.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "danger")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("No se pudo pagar la cuota programada")
        flash("No se pudo registrar el pago; compruebe que no esté duplicado.", "danger")
    return redirect(url_for("gestion.pagos_programados"))


@bp.route("/pagos-programados/cuota/<int:id_cuota>/omitir", methods=["POST"])
def cuota_programada_omitir(id_cuota):
    cuota = CuotaProgramada.query.get_or_404(id_cuota)
    motivo = request.form.get("motivo", "").strip()
    if cuota.estado != "Pendiente":
        flash("La cuota ya fue procesada.", "warning")
    elif not motivo:
        flash("El motivo para omitir la cuota es obligatorio.", "danger")
    else:
        cuota.estado = "Omitido"
        cuota.motivo_omision = motivo[:255]
        db.session.add(Auditoria(modulo="Pagos programados", accion="Omitir cuota", entidad="CuotaProgramada", id_entidad=cuota.id_cuota, detalle=motivo[:255]))
        db.session.commit()
        flash("Cuota omitida sin generar un egreso.", "success")
    return redirect(url_for("gestion.pagos_programados"))


@bp.route("/proveedores", methods=["GET", "POST"])
def proveedores():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
        elif Proveedor.query.filter(db.func.lower(Proveedor.nombre) == nombre.lower()).first():
            flash("El proveedor ya existe.", "danger")
        else:
            try:
                documento = solo_numeros_opcional(request.form.get("documento"), "Documento", 40)
                telefono = solo_numeros_opcional(request.form.get("telefono"), "Teléfono", 50)
                db.session.add(Proveedor(
                    nombre=nombre[:150], telefono=telefono,
                    tipo_persona=request.form.get("tipo_persona", "Persona")[:10],
                    documento=documento,
                    correo=request.form.get("correo", "").strip() or None,
                    contacto=request.form.get("contacto", "").strip() or None,
                    direccion=request.form.get("direccion", "").strip() or None,
                    observacion=request.form.get("observacion", "").strip() or None,
                ))
                db.session.commit()
                flash("Proveedor registrado.", "success")
                return redirect(url_for("gestion.proveedores"))
            except ErrorValidacion as e:
                flash(str(e), "danger")
            except SQLAlchemyError:
                db.session.rollback()
                flash("No se pudo registrar el proveedor; verifique que no esté duplicado.", "danger")
    return render_template("gestion/proveedores.html", proveedores=Proveedor.query.order_by(Proveedor.nombre).all())


@bp.route("/proveedores/<int:id_proveedor>/estado", methods=["POST"])
def proveedor_estado(id_proveedor):
    proveedor = Proveedor.query.get_or_404(id_proveedor)
    proveedor.activo = not proveedor.activo
    db.session.add(Auditoria(modulo="Proveedores", accion="Activar" if proveedor.activo else "Desactivar", entidad="Proveedor", id_entidad=proveedor.id_proveedor, detalle=proveedor.nombre))
    db.session.commit()
    flash("Estado del proveedor actualizado.", "success")
    return redirect(url_for("gestion.proveedores"))


@bp.route("/inventario")
def inventario():
    productos = Producto.query.order_by(Producto.activo.desc(), Producto.nombre).all()
    movimientos = MovimientoInventario.query.order_by(MovimientoInventario.id_movimiento.desc()).limit(30).all()
    return render_template("gestion/inventario.html", productos=productos, movimientos=movimientos)


@bp.route("/inventario/exportar.<formato>")
def inventario_exportar(formato):
    if formato not in {"pdf", "xlsx"}:
        return "Formato no válido", 404
    variantes = ProductoVariante.query.join(Producto).order_by(Producto.nombre, ProductoVariante.talla, ProductoVariante.color).all()
    valores = [[v.producto.codigo, v.producto.nombre, v.producto.categoria, v.talla, v.color,
              f"{v.precio_compra:.2f}", f"{v.precio_venta:.2f}", v.stock, v.stock_minimo,
              "Stock bajo" if v.stock <= v.stock_minimo else "Normal"] for v in variantes]
    encabezados, filas = _campos_reporte("inventario", valores)
    return _enviar_reporte_gestion("Inventario", encabezados, filas, "inventario", formato)


@bp.route("/inventario/conteo", methods=["GET", "POST"])
def inventario_conteo():
    variantes = ProductoVariante.query.join(Producto).order_by(Producto.nombre, ProductoVariante.talla).all()
    if request.method == "POST":
        conteo = ConteoInventario(fecha=date.today(), observacion=request.form.get("observacion", "").strip() or None)
        db.session.add(conteo); db.session.flush()
        for variante in variantes:
            contado = _entero(request.form.get(f"stock_{variante.id_variante}"), "Stock contado", 0)
            db.session.add(DetalleConteoInventario(
                conteo=conteo, variante=variante, stock_sistema=variante.stock, stock_contado=contado
            ))
        db.session.flush()
        db.session.add(Auditoria(modulo="Inventario", accion="Crear conteo", entidad="ConteoInventario", id_entidad=conteo.id_conteo, valor_nuevo=f"variantes={len(variantes)}"))
        db.session.commit(); flash("Conteo guardado pendiente de aprobación.", "success")
        return redirect(url_for("gestion.inventario_conteo"))
    conteos = ConteoInventario.query.order_by(ConteoInventario.id_conteo.desc()).all()
    return render_template("gestion/conteo_inventario.html", variantes=variantes, conteos=conteos)


@bp.route("/inventario/conteo/<int:id_conteo>/aprobar", methods=["POST"])
def inventario_conteo_aprobar(id_conteo):
    conteo = ConteoInventario.query.get_or_404(id_conteo)
    if conteo.estado != "Pendiente":
        flash("Este conteo ya fue procesado.", "warning")
    else:
        for detalle in conteo.detalles:
            variante = detalle.variante
            diferencia = detalle.stock_contado - variante.stock
            if diferencia:
                anterior = variante.stock; variante.stock = detalle.stock_contado
                db.session.add(MovimientoInventario(
                    variante=variante, tipo="Conteo físico", cantidad=diferencia,
                    stock_anterior=anterior, stock_nuevo=variante.stock,
                    motivo=f"Conteo N.º {conteo.id_conteo}", origen_tipo="Conteo", origen_id=conteo.id_conteo,
                ))
        conteo.estado = "Aprobado"
        db.session.add(Auditoria(modulo="Inventario", accion="Aprobar conteo", entidad="ConteoInventario", id_entidad=conteo.id_conteo, valor_nuevo=f"detalles={len(conteo.detalles)}"))
        db.session.commit(); flash("Conteo aprobado y stock conciliado.", "success")
    return redirect(url_for("gestion.inventario_conteo"))


@bp.route("/compras")
def compras():
    return render_template("gestion/compras.html", compras=Compra.query.order_by(Compra.fecha.desc(), Compra.id_compra.desc()).all())


@bp.route("/compras/exportar.<formato>")
def compras_exportar(formato):
    if formato not in {"pdf", "xlsx"}:
        return "Formato no válido", 404
    compras = Compra.query.order_by(Compra.fecha.desc(), Compra.id_compra.desc()).all()
    valores = [[c.id_compra, c.fecha.strftime("%d/%m/%Y"), c.proveedor.nombre, c.numero_factura or "—",
              "; ".join(f"{d.cantidad} × {d.variante.nombre_completo}" for d in c.detalles),
              c.modo_pago, f"{c.total:.2f}", "Activa" if c.activo else "Anulada"] for c in compras]
    encabezados, filas = _campos_reporte("compras", valores)
    return _enviar_reporte_gestion("Compras de inventario", encabezados, filas, "compras", formato)


@bp.route("/compras/nueva", methods=["GET", "POST"])
def compra_nueva():
    proveedores_activos = Proveedor.query.filter_by(activo=True).order_by(Proveedor.nombre).all()
    variantes = ProductoVariante.query.join(Producto).filter(Producto.activo.is_(True)).order_by(Producto.nombre, ProductoVariante.talla).all()
    if request.method == "POST":
        try:
            proveedor = db.session.get(Proveedor, request.form.get("id_proveedor", type=int))
            if not proveedor or not proveedor.activo:
                raise ValueError("Seleccione un proveedor activo.")
            modo = request.form.get("modo_pago", "Efectivo")
            if modo not in MODOS_MOVIMIENTO:
                raise ValueError("El método de pago no es válido.")
            cantidades = request.form.getlist("cantidad")
            costos = request.form.getlist("costo_unitario")
            ids = request.form.getlist("id_variante")
            lineas = []
            for id_texto, cantidad_texto, costo_texto in zip(ids, cantidades, costos):
                cantidad = _entero(cantidad_texto, "Cantidad", 1)
                costo = _decimal(costo_texto, "Costo unitario")
                variante = db.session.get(ProductoVariante, int(id_texto))
                if not variante:
                    raise ValueError("Uno de los productos no existe.")
                lineas.append((variante, cantidad, costo))
            if not lineas:
                raise ValueError("Añada al menos un producto.")
            total = sum((costo * cantidad for _, cantidad, costo in lineas), Decimal("0"))
            compra = Compra(
                proveedor=proveedor, fecha=_fecha(request.form.get("fecha")),
                numero_factura=request.form.get("numero_factura", "").strip() or None,
                modo_pago=modo, total=total,
                observacion=request.form.get("observacion", "").strip() or None,
            )
            db.session.add(compra); db.session.flush()
            for variante, cantidad, costo in lineas:
                anterior = variante.stock; variante.stock += cantidad
                db.session.add(DetalleCompra(compra=compra, variante=variante, cantidad=cantidad, costo_unitario=costo, subtotal=costo*cantidad))
                db.session.add(MovimientoInventario(
                    variante=variante, tipo="Compra", cantidad=cantidad,
                    stock_anterior=anterior, stock_nuevo=variante.stock,
                    origen_tipo="Compra", origen_id=compra.id_compra,
                ))
            db.session.add(MovimientoContable(
                tipo="Egreso", categoria="Compra de inventario",
                concepto=f"Compra N.º {compra.id_compra} - {proveedor.nombre}",
                monto=total, fecha=compra.fecha, modo_pago=modo,
                origen_tipo="Compra", origen_id=compra.id_compra,
            ))
            db.session.add(Auditoria(modulo="Compras", accion="Registrar", entidad="Compra", id_entidad=compra.id_compra, valor_nuevo=f"proveedor={proveedor.nombre}; total={total}"))
            db.session.commit()
            flash("Compra registrada; inventario y finanzas fueron actualizados.", "success")
            return redirect(url_for("gestion.compras"))
        except (ValueError, TypeError) as error:
            db.session.rollback(); flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback(); current_app.logger.exception("No se pudo registrar la compra")
            flash("La compra no se guardó; ningún stock ni egreso fue modificado.", "danger")
    return render_template("gestion/compra_form.html", proveedores=proveedores_activos, variantes=variantes, modos=MODOS_MOVIMIENTO, hoy=date.today().isoformat())


@bp.route("/compras/<int:id_compra>/anular", methods=["POST"])
def compra_anular(id_compra):
    compra = Compra.query.get_or_404(id_compra)
    if not compra.activo:
        flash("La compra ya está anulada.", "warning"); return redirect(url_for("gestion.compras"))
    movimiento = MovimientoContable.query.filter_by(origen_tipo="Compra", origen_id=compra.id_compra).first()
    if movimiento and movimiento.sesion_caja and movimiento.sesion_caja.estado == "Cerrada":
        flash("No puede anular una compra perteneciente a una caja cerrada.", "danger"); return redirect(url_for("gestion.compras"))
    motivo = request.form.get("motivo", "").strip()
    if not motivo:
        flash("El motivo es obligatorio.", "danger"); return redirect(url_for("gestion.compras"))
    try:
        for detalle in compra.detalles:
            if detalle.variante.stock < detalle.cantidad:
                raise ValueError(f"No puede revertirse: el stock de {detalle.variante.nombre_completo} ya fue utilizado.")
        instante = ahora_utc()
        for detalle in compra.detalles:
            anterior = detalle.variante.stock; detalle.variante.stock -= detalle.cantidad
            db.session.add(MovimientoInventario(
                variante=detalle.variante, tipo="Anulación compra", cantidad=-detalle.cantidad,
                stock_anterior=anterior, stock_nuevo=detalle.variante.stock,
                motivo=motivo, origen_tipo="CompraAnulada", origen_id=compra.id_compra,
            ))
        compra.anulado_en=instante; compra.motivo_anulacion=motivo
        if movimiento:
            movimiento.anulado_en=instante; movimiento.motivo_anulacion=motivo
        db.session.add(Auditoria(modulo="Compras", accion="Anular", entidad="Compra", id_entidad=compra.id_compra, valor_anterior=f"total={compra.total}", valor_nuevo=f"anulada; motivo={motivo}"))
        db.session.commit(); flash("Compra anulada; stock y egreso fueron revertidos.", "success")
    except ValueError as error:
        db.session.rollback(); flash(str(error), "danger")
    return redirect(url_for("gestion.compras"))


@bp.route("/inventario/producto/<int:id_producto>/estado", methods=["POST"])
def producto_estado(id_producto):
    producto = Producto.query.get_or_404(id_producto)
    producto.activo = not producto.activo
    db.session.add(Auditoria(modulo="Inventario", accion="Activar" if producto.activo else "Desactivar", entidad="Producto", id_entidad=producto.id_producto, detalle=producto.nombre))
    db.session.commit()
    flash("Estado del producto actualizado.", "success")
    return redirect(url_for("gestion.inventario"))


@bp.route("/inventario/producto", methods=["GET", "POST"])
def producto_nuevo():
    if request.method == "POST":
        try:
            codigo = request.form.get("codigo", "").strip().upper()
            nombre = request.form.get("nombre", "").strip()
            if not codigo or not nombre:
                raise ValueError("Código y nombre son obligatorios.")
            if Producto.query.filter_by(codigo=codigo).first():
                raise ValueError("El código ya está registrado.")
            producto = Producto(
                codigo=codigo[:40], nombre=nombre[:150],
                categoria=request.form.get("categoria", "Uniformes").strip()[:80],
                descripcion=request.form.get("descripcion", "").strip() or None,
            )
            stock_inicial = _entero(
                request.form.get("stock_inicial", 0), "Stock inicial", 0
            )
            variante = ProductoVariante(
                producto=producto,
                talla=request.form.get("talla", "Única").strip() or "Única",
                color=request.form.get("color", "Estándar").strip() or "Estándar",
                precio_compra=_decimal(request.form.get("precio_compra"), "Precio de compra"),
                precio_venta=_decimal(request.form.get("precio_venta"), "Precio de venta"),
                stock=stock_inicial,
                stock_minimo=_entero(request.form.get("stock_minimo", 0), "Stock mínimo"),
            )
            db.session.add(producto)
            db.session.flush()
            if stock_inicial:
                db.session.add(MovimientoInventario(
                    variante=variante, tipo="Stock inicial", cantidad=stock_inicial,
                    stock_anterior=0, stock_nuevo=stock_inicial,
                    motivo="Registro inicial del producto",
                    origen_tipo="Producto", origen_id=producto.id_producto,
                ))
            db.session.add(Auditoria(
                modulo="Inventario", accion="Crear producto", entidad="Producto",
                id_entidad=producto.id_producto,
                valor_nuevo=(
                    f"codigo={producto.codigo}; stock_inicial={stock_inicial}; "
                    f"minimo={variante.stock_minimo}"
                ),
            ))
            db.session.commit()
            flash("Producto y variante registrados.", "success")
            return redirect(url_for("gestion.inventario"))
        except ValueError as error:
            flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback()
            flash("No se pudo registrar el producto; verifique código, talla y color.", "danger")
    return render_template("gestion/producto_form.html")


@bp.route("/inventario/<int:id_producto>/variante", methods=["POST"])
def variante_nueva(id_producto):
    producto = Producto.query.get_or_404(id_producto)
    try:
        variante = ProductoVariante(
            producto=producto,
            talla=request.form.get("talla", "Única").strip() or "Única",
            color=request.form.get("color", "Estándar").strip() or "Estándar",
            precio_compra=_decimal(request.form.get("precio_compra"), "Precio de compra"),
            precio_venta=_decimal(request.form.get("precio_venta"), "Precio de venta"),
            stock=0, stock_minimo=_entero(request.form.get("stock_minimo", 0), "Stock mínimo"),
        )
        db.session.add(variante)
        db.session.commit()
        flash("Variante registrada.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "danger")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("No se pudo actualizar el inventario")
        flash("No se pudo actualizar el inventario. Otro proceso pudo modificar el stock.", "danger")
    except Exception:
        db.session.rollback()
        flash("La talla y el color ya existen para este producto.", "danger")
    return redirect(url_for("gestion.inventario"))


@bp.route("/inventario/<int:id_variante>/precios", methods=["POST"])
def variante_precios(id_variante):
    variante = ProductoVariante.query.get_or_404(id_variante)
    try:
        precio_compra = _decimal(
            request.form.get("precio_compra"), "Precio de compra"
        )
        precio_venta = _decimal(
            request.form.get("precio_venta"), "Precio de venta"
        )
        anterior = (
            f"compra={Decimal(variante.precio_compra):.2f}; "
            f"venta={Decimal(variante.precio_venta):.2f}"
        )
        variante.precio_compra = precio_compra
        variante.precio_venta = precio_venta
        db.session.add(Auditoria(
            modulo="Inventario", accion="Editar precios",
            entidad="ProductoVariante", id_entidad=variante.id_variante,
            valor_anterior=anterior,
            valor_nuevo=f"compra={precio_compra:.2f}; venta={precio_venta:.2f}",
        ))
        db.session.commit()
        flash("Precios actualizados.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "danger")
    return redirect(url_for("gestion.inventario"))


@bp.route("/inventario/<int:id_variante>/movimiento", methods=["POST"])
def inventario_movimiento(id_variante):
    variante = ProductoVariante.query.get_or_404(id_variante)
    if request.form.get("registrar_egreso") == "1":
        bloqueo = _exigir_caja_abierta()
        if bloqueo:
            return bloqueo
    try:
        tipo = request.form.get("tipo")
        cantidad = _entero(request.form.get("cantidad"), "Cantidad", 1)
        if tipo not in {"Entrada", "Ajuste positivo", "Pérdida", "Ajuste negativo"}:
            raise ValueError("El tipo de movimiento no es válido.")
        signo = 1 if tipo in {"Entrada", "Ajuste positivo"} else -1
        nuevo = variante.stock + signo * cantidad
        if nuevo < 0:
            raise ValueError("El movimiento dejaría el inventario con stock negativo.")
        anterior = variante.stock
        variante.stock = nuevo
        movimiento = MovimientoInventario(
            variante=variante, tipo=tipo, cantidad=signo*cantidad,
            stock_anterior=anterior, stock_nuevo=nuevo,
            motivo=request.form.get("motivo", "").strip() or None,
        )
        db.session.add(movimiento)
        db.session.flush()
        if tipo == "Entrada" and request.form.get("registrar_egreso") == "1":
            modo = request.form.get("modo_pago", "Efectivo")
            if modo not in MODOS_MOVIMIENTO:
                raise ValueError("El método de pago no es válido.")
            total = Decimal(variante.precio_compra) * cantidad
            db.session.add(MovimientoContable(
                tipo="Egreso", categoria="Compra de inventario",
                concepto=f"Compra {variante.nombre_completo}", monto=total,
                fecha=date.today(), modo_pago=modo,
                origen_tipo="Inventario", origen_id=movimiento.id_movimiento,
            ))
        db.session.commit()
        flash("Inventario actualizado.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "danger")
    return redirect(url_for("gestion.inventario"))


@bp.route("/ventas")
def ventas():
    return render_template("gestion/ventas.html", ventas=Venta.query.order_by(Venta.fecha.desc(), Venta.id_venta.desc()).all())


@bp.route("/ventas/exportar.<formato>")
def ventas_exportar(formato):
    if formato not in {"pdf", "xlsx"}:
        return "Formato no válido", 404
    ventas = Venta.query.order_by(Venta.fecha.desc(), Venta.id_venta.desc()).all()
    valores = [[v.id_venta, v.fecha.strftime("%d/%m/%Y"),
              v.alumno.nombre_completo if v.alumno else (v.cliente_externo or "Público general"),
              "; ".join(f"{d.cantidad} × {d.variante.nombre_completo}" for d in v.detalles),
              v.modo_pago, f"{v.subtotal:.2f}", f"{v.descuento:.2f}", f"{v.total:.2f}",
              "Vigente" if v.activo else "Anulada"] for v in ventas]
    encabezados, filas = _campos_reporte("ventas", valores)
    return _enviar_reporte_gestion("Ventas", encabezados, filas, "ventas", formato)


@bp.route("/ventas/<int:id_venta>/recibo.pdf")
def venta_recibo(id_venta):
    venta = Venta.query.get_or_404(id_venta)
    config, logo = configuracion_y_logo()
    cliente = venta.alumno.nombre_completo if venta.alumno else (venta.cliente_externo or "Público general")
    filas = [[d.cantidad, d.variante.nombre_completo, f"{d.precio_unitario:.2f}", f"{d.subtotal:.2f}"] for d in venta.detalles]
    filas.extend([["", "Subtotal", "", f"{venta.subtotal:.2f}"], ["", "Descuento", "", f"{venta.descuento:.2f}"], ["", "TOTAL", "", f"{venta.total:.2f}"]])
    titulo = f"{config.nombre_academia} - Recibo de venta N.º {venta.id_venta} - {cliente}"
    archivo = generar_tabla_pdf(titulo, ["Cantidad", "Producto", "Precio", "Subtotal"], filas, orientacion="vertical", logo_path=logo)
    return send_file(archivo, mimetype="application/pdf", as_attachment=True, download_name=f"venta_{venta.id_venta}.pdf")


@bp.route("/ventas/nueva", methods=["GET", "POST"])
def venta_nueva():
    variantes = ProductoVariante.query.join(Producto).filter(Producto.activo.is_(True)).order_by(Producto.nombre, ProductoVariante.talla).all()
    alumnos = Alumno.query.filter_by(estado="Activo").order_by(Alumno.apellido, Alumno.nombre).all()
    if request.method == "POST":
        try:
            ids = request.form.getlist("id_variante")
            cantidades = request.form.getlist("cantidad")
            cantidades_por_variante = {}
            for id_texto, cantidad_texto in zip(ids, cantidades):
                if not id_texto or not cantidad_texto:
                    continue
                variante = db.session.get(ProductoVariante, int(id_texto))
                cantidad = _entero(cantidad_texto, "Cantidad", 1)
                if not variante:
                    raise ValueError("Uno de los productos no existe.")
                cantidades_por_variante[variante.id_variante] = cantidades_por_variante.get(variante.id_variante, 0) + cantidad
            lineas = []
            for id_variante, cantidad in cantidades_por_variante.items():
                variante = db.session.get(ProductoVariante, id_variante)
                if cantidad > variante.stock:
                    raise ValueError("No existe stock suficiente para uno de los productos.")
                lineas.append((variante, cantidad))
            if not lineas:
                raise ValueError("Seleccione al menos un producto.")
            descuento = _decimal(request.form.get("descuento"), "Descuento")
            subtotal = sum((Decimal(v.precio_venta) * c for v, c in lineas), Decimal("0"))
            if descuento > subtotal:
                raise ValueError("El descuento no puede superar el subtotal.")
            modo = request.form.get("modo_pago", "Efectivo")
            if modo not in MODOS_MOVIMIENTO:
                raise ValueError("El método de pago no es válido.")
            id_alumno = request.form.get("id_alumno", type=int)
            cliente_externo = request.form.get("cliente_externo", "").strip() or None
            if not id_alumno and not cliente_externo:
                raise ValueError("Seleccione un alumno o escriba el nombre del cliente.")
            if id_alumno and not db.session.get(Alumno, id_alumno):
                raise ValueError("El alumno seleccionado no existe.")
            venta = Venta(
                id_alumno=id_alumno,
                cliente_externo=cliente_externo,
                fecha=_fecha(request.form.get("fecha")), modo_pago=modo,
                numero_operacion=request.form.get("numero_operacion", "").strip() or None,
                subtotal=subtotal, descuento=descuento, total=subtotal-descuento,
                observacion=request.form.get("observacion", "").strip() or None,
            )
            db.session.add(venta)
            db.session.flush()
            for variante, cantidad in lineas:
                anterior = variante.stock
                variante.stock -= cantidad
                db.session.add(DetalleVenta(
                    venta=venta, variante=variante, cantidad=cantidad,
                    precio_unitario=variante.precio_venta,
                    subtotal=Decimal(variante.precio_venta)*cantidad,
                ))
                db.session.add(MovimientoInventario(
                    variante=variante, tipo="Venta", cantidad=-cantidad,
                    stock_anterior=anterior, stock_nuevo=variante.stock,
                    origen_tipo="Venta", origen_id=venta.id_venta,
                ))
            db.session.add(MovimientoContable(
                tipo="Ingreso", categoria="Venta de productos",
                concepto=f"Venta N.º {venta.id_venta}", monto=venta.total,
                fecha=venta.fecha, modo_pago=venta.modo_pago,
                numero_operacion=venta.numero_operacion,
                origen_tipo="Venta", origen_id=venta.id_venta,
            ))
            db.session.add(Auditoria(
                modulo="Ventas", accion="Registrar", entidad="Venta",
                id_entidad=venta.id_venta, detalle=f"Total {venta.total}",
            ))
            db.session.commit()
            flash("Venta registrada e inventario actualizado.", "success")
            return redirect(url_for("gestion.ventas"))
        except (ValueError, TypeError) as error:
            db.session.rollback()
            flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("No se pudo registrar la venta")
            flash("No se pudo registrar la venta. Revise el stock e intente nuevamente.", "danger")
    return render_template("gestion/venta_form.html", variantes=variantes, alumnos=alumnos, modos=MODOS_MOVIMIENTO, hoy=date.today().isoformat())


@bp.route("/ventas/<int:id_venta>/devolver", methods=["POST"])
def venta_devolver(id_venta):
    venta = Venta.query.get_or_404(id_venta)
    try:
        if not venta.activo:
            raise ValueError("No se puede devolver productos de una venta anulada.")
        detalle = db.session.get(DetalleVenta, request.form.get("id_detalle", type=int))
        cantidad = _entero(request.form.get("cantidad"), "Cantidad", 1)
        motivo = request.form.get("motivo", "").strip()
        if not detalle or detalle.id_venta != venta.id_venta or not motivo:
            raise ValueError("Seleccione un producto e indique el motivo.")
        ya_devuelto = sum(d.cantidad for devolucion in venta.devoluciones for d in devolucion.detalles if d.id_detalle_venta == detalle.id_detalle)
        if cantidad + ya_devuelto > detalle.cantidad:
            raise ValueError("La cantidad supera las unidades disponibles para devolución.")
        credito = Decimal(detalle.precio_unitario) * cantidad
        devolucion = DevolucionVenta(venta=venta, fecha=date.today(), total_credito=credito, motivo=motivo[:255])
        db.session.add(devolucion); db.session.flush()
        db.session.add(DetalleDevolucionVenta(devolucion=devolucion, detalle_venta=detalle, cantidad=cantidad, subtotal=credito))
        variante = detalle.variante; anterior = variante.stock; variante.stock += cantidad
        db.session.add(MovimientoInventario(
            variante=variante, tipo="Devolución", cantidad=cantidad,
            stock_anterior=anterior, stock_nuevo=variante.stock,
            origen_tipo="DevolucionVenta", origen_id=devolucion.id_devolucion,
        ))
        db.session.add(MovimientoContable(
            tipo="Egreso", categoria="Devoluciones de venta", concepto=f"Devolución venta N.º {venta.id_venta}",
            monto=credito, fecha=date.today(), modo_pago=venta.modo_pago,
            origen_tipo="DevolucionVenta", origen_id=devolucion.id_devolucion,
        ))
        db.session.add(Auditoria(
            modulo="Ventas", accion="Devolución parcial", entidad="DevolucionVenta",
            id_entidad=devolucion.id_devolucion,
            valor_nuevo=f"venta={venta.id_venta}; producto={detalle.id_detalle}; cantidad={cantidad}; crédito={credito}; motivo={motivo[:255]}",
        ))
        db.session.commit(); flash("Devolución parcial registrada y stock restituido.", "success")
    except ValueError as error:
        db.session.rollback(); flash(str(error), "danger")
    return redirect(url_for("gestion.ventas"))


@bp.route("/ventas/<int:id_venta>/anular", methods=["POST"])
def venta_anular(id_venta):
    venta = Venta.query.get_or_404(id_venta)
    motivo = request.form.get("motivo", "").strip()
    movimiento_origen = MovimientoContable.query.filter_by(origen_tipo="Venta", origen_id=venta.id_venta).first()
    if not venta.activo:
        flash("La venta ya está anulada.", "warning")
    elif not motivo:
        flash("El motivo es obligatorio.", "danger")
    elif venta.devoluciones:
        flash("No puede anularse completamente una venta que ya tiene devoluciones parciales. Mantenga la venta activa para conservar la trazabilidad.", "danger")
    elif movimiento_origen and movimiento_origen.sesion_caja and movimiento_origen.sesion_caja.estado == "Cerrada":
        flash("No puede anular una venta perteneciente a una caja cerrada.", "danger")
    else:
        venta.anulado_en = ahora_utc()
        venta.motivo_anulacion = motivo[:255]
        for detalle in venta.detalles:
            anterior = detalle.variante.stock
            detalle.variante.stock += detalle.cantidad
            db.session.add(MovimientoInventario(
                variante=detalle.variante, tipo="Devolución",
                cantidad=detalle.cantidad, stock_anterior=anterior,
                stock_nuevo=detalle.variante.stock,
                motivo=motivo, origen_tipo="Anulación venta", origen_id=venta.id_venta,
            ))
        movimiento = MovimientoContable.query.filter_by(origen_tipo="Venta", origen_id=venta.id_venta).first()
        if movimiento:
            movimiento.anulado_en = venta.anulado_en
            movimiento.motivo_anulacion = motivo[:255]
        db.session.add(Auditoria(
            modulo="Ventas", accion="Anular", entidad="Venta",
            id_entidad=venta.id_venta, detalle=motivo,
        ))
        db.session.commit()
        flash("Venta anulada y existencias restituidas.", "success")
    return redirect(url_for("gestion.ventas"))
