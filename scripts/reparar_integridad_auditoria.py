"""Repara inconsistencias comprobables detectadas por la auditoría interna."""
import argparse
from collections import defaultdict

from app import create_app
from app.extensions import db
from app.models import (
    Auditoria, Compra, EventoAgenda, MovimientoContable, Pago, Partido, Venta,
    AplicacionPago, Obligacion,
)
from app.utils.backup import crear_respaldo_completo


def _crear_movimientos_ausentes():
    creados = []
    pagos = Pago.query.filter(Pago.eliminado_en.is_(None), Pago.es_beca.is_(False), Pago.monto > 0).all()
    for pago in pagos:
        if not MovimientoContable.query.filter_by(origen_tipo="Pago", origen_id=pago.id_pago).first():
            db.session.add(MovimientoContable(
                tipo="Ingreso", categoria="Mensualidades",
                concepto=f"Mensualidad {pago.mes_pagado} - {pago.alumno.nombre_completo}",
                monto=pago.monto, fecha=pago.fecha_pago, modo_pago=pago.modo_pago,
                numero_operacion=pago.numero_operacion, origen_tipo="Pago", origen_id=pago.id_pago,
            ))
            creados.append(f"Pago:{pago.id_pago}")
    for venta in Venta.query.filter(Venta.anulado_en.is_(None)).all():
        if not MovimientoContable.query.filter_by(origen_tipo="Venta", origen_id=venta.id_venta).first():
            db.session.add(MovimientoContable(
                tipo="Ingreso", categoria="Venta de productos", concepto=f"Venta N.º {venta.id_venta}",
                monto=venta.total, fecha=venta.fecha, modo_pago=venta.modo_pago,
                numero_operacion=venta.numero_operacion, origen_tipo="Venta", origen_id=venta.id_venta,
            ))
            creados.append(f"Venta:{venta.id_venta}")
    for compra in Compra.query.filter(Compra.anulado_en.is_(None)).all():
        if not MovimientoContable.query.filter_by(origen_tipo="Compra", origen_id=compra.id_compra).first():
            db.session.add(MovimientoContable(
                tipo="Egreso", categoria="Compra de inventario",
                concepto=f"Compra N.º {compra.id_compra} - {compra.proveedor.nombre}",
                monto=compra.total, fecha=compra.fecha, modo_pago=compra.modo_pago,
                origen_tipo="Compra", origen_id=compra.id_compra,
            ))
            creados.append(f"Compra:{compra.id_compra}")
    return creados


def _sincronizar_agenda_partidos():
    sincronizados = []
    partidos = Partido.query.all()
    for partido in partidos:
        evento = EventoAgenda.query.filter_by(id_partido=partido.id_partido).first()
        if evento is None:
            evento = EventoAgenda(id_partido=partido.id_partido, tipo="Partido")
            db.session.add(evento)
            sincronizados.append(partido.id_partido)
        evento.fecha = partido.fecha
        evento.hora = partido.hora
        evento.descripcion = f"Partido vs {partido.rival}"
        evento.lugar = partido.cancha
        evento.id_lugar = partido.id_lugar
        evento.id_categoria = partido.id_categoria
        evento.id_equipo = partido.id_equipo
    return sincronizados


def _reparar_aplicaciones_pago():
    reparados = []
    pagos = Pago.query.filter(Pago.eliminado_en.is_(None)).all()
    for pago in pagos:
        tiene_aplicacion = AplicacionPago.query.filter_by(id_pago=pago.id_pago).first()
        if not tiene_aplicacion:
            obligacion = Obligacion.query.filter_by(
                id_alumno=pago.id_alumno, concepto="Mensualidad", periodo=pago.mes_pagado
            ).first()
            if not obligacion:
                obligacion = Obligacion(
                    id_alumno=pago.id_alumno, concepto="Mensualidad", periodo=pago.mes_pagado,
                    monto_original=pago.monto, descuento=0, recargo=0,
                    cubierto_beca=pago.es_beca, fecha_vencimiento=pago.fecha_vencimiento or pago.fecha_pago,
                )
                db.session.add(obligacion)
                db.session.flush()
            db.session.add(AplicacionPago(
                id_obligacion=obligacion.id_obligacion,
                id_pago=pago.id_pago,
                monto=pago.monto,
            ))
            reparados.append(pago.id_pago)
    return reparados


def _depurar_partidos_duplicados():
    grupos = defaultdict(list)
    for partido in Partido.query.all():
        clave = (
            partido.fecha, partido.hora, partido.id_equipo, partido.id_equipo_rival,
            (partido.rival or "").strip().lower(), partido.id_campeonato,
            partido.id_categoria, partido.id_lugar,
        )
        grupos[clave].append(partido)
    eliminados, omitidos = [], []
    for partidos in grupos.values():
        if len(partidos) < 2:
            continue
        partidos.sort(key=lambda p: p.id_partido)
        dependencias = Partido.query.filter(db.or_(
            Partido.id_partido_origen_local.in_([p.id_partido for p in partidos[1:]]),
            Partido.id_partido_origen_visita.in_([p.id_partido for p in partidos[1:]]),
        )).first()
        con_resultado = any(
            p.resultado or p.goles_local is not None or p.goles_visita is not None
            or p.estado_partido in {"Finalizado", "Walkover"} for p in partidos
        )
        if con_resultado or dependencias:
            omitidos.append([p.id_partido for p in partidos])
            continue
        for duplicado in partidos[1:]:
            EventoAgenda.query.filter_by(id_partido=duplicado.id_partido).delete(synchronize_session=False)
            eliminados.append(duplicado.id_partido)
            db.session.delete(duplicado)
    return eliminados, omitidos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirmar", action="store_true")
    args = parser.parse_args()
    if not args.confirmar:
        raise SystemExit("Use --confirmar para aplicar la reparación.")
    app = create_app()
    with app.app_context():
        respaldo = crear_respaldo_completo(app)
        movimientos = _crear_movimientos_ausentes()
        partidos, omitidos = _depurar_partidos_duplicados()
        agenda_partidos = _sincronizar_agenda_partidos()
        aplicaciones = _reparar_aplicaciones_pago()
        db.session.add(Auditoria(
            modulo="Integridad", accion="Reparación de auditoría", entidad="Sistema",
            valor_anterior=f"movimientos_ausentes={len(movimientos)}; duplicados={len(partidos)}; agenda={len(agenda_partidos)}; aplicaciones={len(aplicaciones)}",
            valor_nuevo=f"movimientos={len(movimientos)}; partidos_eliminados={len(partidos)}; agenda_sincronizada={len(agenda_partidos)}; aplicaciones_reparadas={len(aplicaciones)}; respaldo={respaldo}",
        ))
        db.session.commit()
        print(f"Respaldo: {respaldo}")
        print(f"Movimientos reconstruidos: {len(movimientos)} ({', '.join(movimientos)})")
        print(f"Partidos duplicados eliminados: {len(partidos)}")
        print(f"Grupos omitidos por resultados o dependencias: {len(omitidos)}")
        print(f"Partidos proyectados en agenda: {len(agenda_partidos)}")
        print(f"Aplicaciones de pago reparadas: {len(aplicaciones)}")



if __name__ == "__main__":
    main()
