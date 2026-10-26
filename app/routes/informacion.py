from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
import os

from pathlib import Path
from flask import (
    Blueprint, render_template, current_app, send_file, flash, redirect, url_for,
)
from sqlalchemy.orm import selectinload, joinedload

from app.extensions import db
from app.models import (Alumno, Auditoria, Categoria, CuotaProgramada, Equipo, EventoAgenda,
    MovimientoCaja, MovimientoContable, Partido, Pago, CierreCaja, Obligacion, AplicacionPago,
    Producto, ProductoVariante, Compra, Venta, DevolucionVenta, ConteoInventario,
    PersonalDeportivo, AsistenciaEntrenamiento, SesionCaja, InscripcionGestion)
from app.utils.resumen_categorias import construir_resumen_categorias
from app.utils.backup import crear_respaldo, crear_respaldo_completo, ruta_sqlite
from app.utils.descargas import carpeta_descargas, guardar_archivo
from app.utils.integridad import auditar_sqlite


bp = Blueprint("informacion", __name__, url_prefix="/informacion")


def _calcular_recaudacion_mes(hoy=None):
    hoy = hoy or date.today()
    inicio_mes = hoy.replace(day=1)
    pagos_mes = (
        Pago.query
        .filter(
            Pago.eliminado_en.is_(None),
            Pago.fecha_pago >= inicio_mes,
            Pago.fecha_pago <= hoy,
        )
        .all()
    )
    recaudacion_mes = sum(
        (Decimal(pago.monto or 0) for pago in pagos_mes if not pago.es_beca),
        Decimal("0"),
    )
    recaudacion_por_modo = {
        modo: sum(
            (
                Decimal(pago.monto or 0)
                for pago in pagos_mes
                if not pago.es_beca and pago.modo_pago == modo
            ),
            Decimal("0"),
        )
        for modo in ("Efectivo", "QR")
    }
    return pagos_mes, recaudacion_mes, recaudacion_por_modo


@bp.route("/respaldo-completo", methods=["POST"])
def respaldo_completo():
    destino = crear_respaldo_completo(current_app)
    copia_descarga = guardar_archivo(destino, "respaldos")
    current_app.logger.info("Respaldo completo solicitado desde el panel: %s", destino)
    return send_file(
        copia_descarga,
        mimetype="application/zip",
        as_attachment=True,
        download_name=copia_descarga.name,
    )


@bp.route("/abrir-descargas", methods=["POST"])
def abrir_descargas():
    carpeta = carpeta_descargas()
    if os.name != "nt" or not hasattr(os, "startfile"):
        flash(f"Carpeta de descargas: {carpeta}", "info")
    else:
        os.startfile(carpeta)
        flash("Carpeta de descargas abierta.", "success")
    return redirect(url_for("informacion.general"))


@bp.route("/")
def general():
    """Resumen operativo de la academia sin duplicar alumnos por equipo."""
    hoy = date.today()

    alumnos = (
        Alumno.query
        .options(selectinload(Alumno.equipos), selectinload(Alumno.categoria))
        .order_by(Alumno.apellido, Alumno.nombre)
        .all()
    )
    ids_alumnos = [alumno.id_alumno for alumno in alumnos]
    pagos = []
    if ids_alumnos:
        pagos = (
            Pago.query
            .filter(Pago.eliminado_en.is_(None), Pago.id_alumno.in_(ids_alumnos))
            .order_by(Pago.fecha_vencimiento.desc(), Pago.fecha_pago.desc(), Pago.id_pago.desc())
            .all()
        )

    reactivacion_por_alumno = {
        alumno.id_alumno: alumno.fecha_ultima_reactivacion.strftime("%Y-%m")
        for alumno in alumnos if alumno.fecha_ultima_reactivacion
    }
    ultimo_pago = {}
    for pago in pagos:
        mes_inicio = reactivacion_por_alumno.get(pago.id_alumno)
        if mes_inicio and pago.mes_pagado < mes_inicio:
            continue
        ultimo_pago.setdefault(pago.id_alumno, pago)

    activos = [alumno for alumno in alumnos if alumno.estado == "Activo"]
    retirados = [alumno for alumno in alumnos if alumno.estado == "Retirado"]
    estados_mensualidad = Counter(
        ultimo_pago[alumno.id_alumno].estado_cobertura
        if alumno.id_alumno in ultimo_pago else "Sin pagos"
        for alumno in activos
    )

    pagos_mes, recaudacion_mes, recaudacion_por_modo = (
        _calcular_recaudacion_mes(hoy)
    )

    categorias = Categoria.query.order_by(Categoria.edad_min, Categoria.nombre).all()
    equipos = (
        Equipo.query
        .filter_by(es_rival=False)
        .options(selectinload(Equipo.alumnos), selectinload(Equipo.categoria))
        .order_by(Equipo.nombre)
        .all()
    )
    resumen_categorias = construir_resumen_categorias(
        categorias, equipos, alumnos, solo_activos=True
    )

    resumen_equipos = []
    for equipo in equipos:
        integrantes = {
            alumno.id_alumno: alumno
            for alumno in equipo.alumnos
            if alumno.estado == "Activo"
        }
        resumen_equipos.append({
            "equipo": equipo,
            "total": len(integrantes),
            "deben": sum(
                1 for alumno in integrantes.values()
                if (
                    alumno.id_alumno not in ultimo_pago
                    or ultimo_pago[alumno.id_alumno].estado_cobertura == "Vencido"
                )
            ),
        })

    becas = Counter(alumno.beca_vigente for alumno in activos)
    becas_vencidas = sum(
        1 for alumno in activos
        if alumno.beca != "Ninguna"
        and alumno.beca_fecha_fin is not None
        and alumno.beca_fecha_fin < hoy
    )
    proximos_eventos = (
        EventoAgenda.query
        .filter(EventoAgenda.fecha >= hoy)
        .order_by(EventoAgenda.fecha, EventoAgenda.hora)
        .limit(8)
        .all()
    )
    cuotas_pendientes = CuotaProgramada.query.filter(
        CuotaProgramada.estado == "Pendiente",
        CuotaProgramada.fecha_vencimiento <= hoy + timedelta(days=30),
    ).order_by(CuotaProgramada.fecha_vencimiento).all()
    inicio_mes = hoy.replace(day=1)
    obligaciones_pendientes = [
        o for o in Obligacion.query.options(
            selectinload(Obligacion.aplicaciones).joinedload(AplicacionPago.pago)
        ).all() if o.saldo > 0
    ]
    movimientos_mes = MovimientoContable.query.filter(
        MovimientoContable.fecha >= inicio_mes, MovimientoContable.fecha <= hoy,
        MovimientoContable.anulado_en.is_(None),
    ).all()
    ingresos_mes = sum((Decimal(m.monto) for m in movimientos_mes if m.tipo == "Ingreso"), Decimal("0"))
    egresos_mes = sum((Decimal(m.monto) for m in movimientos_mes if m.tipo == "Egreso"), Decimal("0"))
    variantes = ProductoVariante.query.join(Producto).filter(
        Producto.activo.is_(True)
    ).all()
    asistencias_mes = AsistenciaEntrenamiento.query.filter(
        AsistenciaEntrenamiento.registrado_en >= inicio_mes
    ).all()
    presentes_mes = sum(1 for a in asistencias_mes if a.estado in {"Presente", "Tarde"})
    proximos_cumpleanos = []
    for alumno in activos:
        try:
            cumple = alumno.fecha_nacimiento.replace(year=hoy.year)
        except ValueError:
            cumple = date(hoy.year, 2, 28)
        if cumple < hoy:
            try: cumple = alumno.fecha_nacimiento.replace(year=hoy.year + 1)
            except ValueError: cumple = date(hoy.year + 1, 2, 28)
        dias = (cumple - hoy).days
        if dias <= 30:
            proximos_cumpleanos.append((alumno, cumple, dias))
    proximos_cumpleanos.sort(key=lambda item: item[1])

    indicadores = {
        "alumnos": len(activos),
        "activos": len(activos),
        "retirados": len(retirados),
        "vigentes": estados_mensualidad["Vigente"],
        "proximos": estados_mensualidad["Próximo a vencer"],
        "vencidos": estados_mensualidad["Vencido"],
        "sin_pagos": estados_mensualidad["Sin pagos"],
        "deben": estados_mensualidad["Vencido"] + estados_mensualidad["Sin pagos"],
        "categorias": len(categorias),
        "equipos": len(equipos),
        "pagos_mes": len(pagos_mes),
        "recaudacion_mes": recaudacion_mes,
        "obligaciones_pendientes": len(obligaciones_pendientes),
        "saldo_pendiente": sum((o.saldo for o in obligaciones_pendientes), Decimal("0")),
        "ingresos_finanzas_mes": ingresos_mes, "egresos_finanzas_mes": egresos_mes,
        "saldo_finanzas_mes": ingresos_mes - egresos_mes,
        "stock_bajo": sum(1 for v in variantes if v.stock <= v.stock_minimo),
        "compras_mes": Compra.query.filter(Compra.fecha >= inicio_mes, Compra.fecha <= hoy, Compra.anulado_en.is_(None)).count(),
        "ventas_mes": Venta.query.filter(Venta.fecha >= inicio_mes, Venta.fecha <= hoy, Venta.anulado_en.is_(None)).count(),
        "devoluciones_mes": DevolucionVenta.query.filter(DevolucionVenta.fecha >= inicio_mes, DevolucionVenta.fecha <= hoy).count(),
        "conteos_pendientes": ConteoInventario.query.filter_by(estado="Pendiente").count(),
        "personal_activo": PersonalDeportivo.query.filter_by(activo=True).count(),
        "asistencia_mes": round((presentes_mes / len(asistencias_mes) * 100), 1) if asistencias_mes else 0,
        "cajas_abiertas": SesionCaja.query.filter(SesionCaja.estado.in_(("Abierta", "Reabierta"))).count(),
        "inscripciones_activas": InscripcionGestion.query.filter_by(gestion=hoy.year, estado="Activa").count(),
    }
    ultimo_cierre = CierreCaja.query.order_by(CierreCaja.fecha.desc()).first()
    ruta_base = ruta_sqlite(current_app)
    respaldos = ruta_base.parent / "backups" if ruta_base else Path()
    ultimo_respaldo = max(
        respaldos.glob("academia_completo_*.zip"), key=lambda ruta: ruta.stat().st_mtime,
        default=None,
    ) if respaldos.exists() else None
    return render_template(
        "informacion/general.html",
        indicadores=indicadores,
        resumen_categorias=resumen_categorias,
        resumen_equipos=resumen_equipos,
        recaudacion_por_modo=recaudacion_por_modo,
        becas=becas,
        becas_vencidas=becas_vencidas,
        proximos_eventos=proximos_eventos,
        cuotas_pendientes=cuotas_pendientes,
        proximos_cumpleanos=proximos_cumpleanos,
        ultimo_cierre=ultimo_cierre,
        ultimo_respaldo=ultimo_respaldo,
        carpeta_descargas=carpeta_descargas(),
        hoy=hoy,
    )


@bp.route("/auditoria")
def auditoria():
    ruta = ruta_sqlite(current_app)
    resultado = auditar_sqlite(ruta) if ruta else {
        "correcta": False, "alertas": ["La base configurada no es SQLite."],
        "sin_pk": [], "fks_invalidas": [], "indices_recomendados": [],
        "tablas": [], "estadisticas": {}, "integridad": "no disponible",
    }
    registros = Auditoria.query.order_by(Auditoria.creado_en.desc(), Auditoria.id_auditoria.desc()).limit(200).all()
    return render_template("informacion/auditoria.html", resultado=resultado, registros=registros)


@bp.route("/auditoria/reparar-vinculos-caja", methods=["POST"])
def reparar_vinculos_caja():
    respaldo = crear_respaldo(current_app, "antes_reparar_integridad")
    faltantes = MovimientoContable.query.filter(
        MovimientoContable.id_sesion_caja.is_not(None),
        ~MovimientoContable.id_movimiento.in_(db.select(MovimientoCaja.id_movimiento_contable)),
    ).all()
    for movimiento in faltantes:
        db.session.add(MovimientoCaja(
            id_sesion=movimiento.id_sesion_caja,
            id_movimiento_contable=movimiento.id_movimiento,
            tipo=movimiento.tipo, monto=movimiento.monto,
            modo_pago=movimiento.modo_pago, creado_en=movimiento.creado_en,
        ))
    proyecciones = 0
    for partido in Partido.query.all():
        evento = EventoAgenda.query.filter_by(id_partido=partido.id_partido).first()
        if not evento:
            evento = EventoAgenda(id_partido=partido.id_partido, tipo="Partido")
            db.session.add(evento)
        evento.fecha=partido.fecha; evento.hora=partido.hora
        evento.descripcion=f"Partido vs {partido.rival}"; evento.lugar=partido.cancha
        evento.id_lugar=partido.id_lugar; evento.id_categoria=partido.id_categoria
        evento.id_equipo=partido.id_equipo; proyecciones += 1
    db.session.add(Auditoria(
        modulo="Integridad", accion="Reparar vínculos de caja", entidad="MovimientoCaja",
        valor_nuevo=f"caja={len(faltantes)}; agenda_sincronizada={proyecciones}; respaldo={respaldo}",
    ))
    db.session.commit()
    flash(f"Reparación controlada terminada: {len(faltantes)} vínculos de caja y {proyecciones} proyecciones deportivas verificadas.", "success")
    return redirect(url_for("informacion.auditoria"))


@bp.route("/recaudacion-mes")
def recaudacion_mes():
    pagos_mes, total, por_modo = _calcular_recaudacion_mes()
    return render_template(
        "informacion/_recaudacion_mes.html",
        recaudacion_mes=total,
        recaudacion_por_modo=por_modo,
        cantidad_pagos=len(pagos_mes),
    )
