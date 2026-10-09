"""Normaliza los importes demo a un flujo mensual realista e idempotente."""
from pathlib import Path
import sys
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text, bindparam
from app import create_app
from app.extensions import db


def ejecutar():
    hoy = date.today().isoformat()
    ids = [r[0] for r in db.session.execute(text("""SELECT m.id_movimiento
        FROM movimiento_contable m LEFT JOIN cuota_programada c
        ON m.origen_tipo='CuotaProgramada' AND m.origen_id=c.id_cuota
        LEFT JOIN pago_programado p ON p.id_programado=c.id_programado
        WHERE p.concepto LIKE '[DEMO]%' OR m.concepto LIKE '[DEMO]%'""")).all()]
    if ids:
        for sql in ("DELETE FROM movimiento_caja WHERE id_movimiento_contable IN :ids",
                    "UPDATE cuota_programada SET id_movimiento=NULL WHERE id_movimiento IN :ids",
                    "DELETE FROM movimiento_contable WHERE id_movimiento IN :ids"):
            db.session.execute(text(sql).bindparams(bindparam("ids", expanding=True)), {"ids": ids})
    importes = {
        "[DEMO] Alquiler mensual": 900,
        "[DEMO] Pago quincenal entrenador": 350,
        "[DEMO] Servicio pausado": 180,
    }
    for concepto, monto in importes.items():
        db.session.execute(text("UPDATE pago_programado SET monto=:m WHERE concepto=:c"), {"m": monto, "c": concepto})
        db.session.execute(text("""UPDATE cuota_programada SET monto=:m,estado='Pendiente',
            fecha_pago=NULL,id_movimiento=NULL,motivo_omision=NULL WHERE id_programado=(
            SELECT id_programado FROM pago_programado WHERE concepto=:c)"""), {"m": monto, "c": concepto})
    # Una cuota pagada por cada obligación activa y una cuota omitida para
    # mostrar el caso, sin convertir todas las cuotas futuras en egresos.
    for concepto, categoria in (("[DEMO] Alquiler mensual", "Alquiler"),
                                ("[DEMO] Pago quincenal entrenador", "Pago a profesores")):
        cuota = db.session.execute(text("""SELECT c.id_cuota,c.monto FROM cuota_programada c
            JOIN pago_programado p ON p.id_programado=c.id_programado
            WHERE p.concepto=:c AND c.fecha_vencimiento<=:h
            ORDER BY c.fecha_vencimiento DESC LIMIT 1"""), {"c": concepto, "h": hoy}).first()
        if cuota:
            movimiento = db.session.execute(text("""INSERT INTO movimiento_contable
                (tipo,categoria,id_categoria_contable,concepto,monto,fecha,modo_pago,
                 origen_tipo,origen_id,creado_en)
                VALUES ('Egreso',:cat,(SELECT id_categoria_contable FROM categoria_contable WHERE nombre=:cat),
                :con,:m,:h,'Efectivo','CuotaProgramada',:id,CURRENT_TIMESTAMP) RETURNING id_movimiento"""),
                {"cat": categoria, "con": concepto, "m": cuota.monto, "h": hoy, "id": cuota.id_cuota}).scalar()
            db.session.execute(text("UPDATE cuota_programada SET estado='Pagado',fecha_pago=:h,id_movimiento=:m WHERE id_cuota=:id"),
                               {"h": hoy, "m": movimiento, "id": cuota.id_cuota})
    omitida = db.session.execute(text("""SELECT c.id_cuota FROM cuota_programada c JOIN pago_programado p
        ON p.id_programado=c.id_programado WHERE p.concepto='[DEMO] Pago quincenal entrenador'
        AND c.estado='Pendiente' AND c.fecha_vencimiento<=:h ORDER BY c.fecha_vencimiento DESC LIMIT 1"""), {"h": hoy}).scalar()
    if omitida:
        db.session.execute(text("UPDATE cuota_programada SET estado='Omitido',motivo_omision='Clase suspendida (caso demo)' WHERE id_cuota=:id"), {"id": omitida})
    # Flujo mensual estimado: 40 alumnos pagando Bs 130, más venta de uniformes.
    for tipo, categoria, concepto, monto in (
        ("Ingreso", "Mensualidades", "[DEMO] Recaudación mensual estimada (40 alumnos)", 5200),
        ("Ingreso", "Uniformes", "[DEMO] Ventas de uniformes del mes", 360),
        ("Egreso", "Equipo deportivo", "[DEMO] Reposición de material deportivo", 250),
    ):
        db.session.execute(text("""INSERT INTO movimiento_contable
            (tipo,categoria,id_categoria_contable,concepto,monto,fecha,modo_pago,creado_en)
            VALUES (:t,:c,(SELECT id_categoria_contable FROM categoria_contable WHERE nombre=:c),
            :x,:m,:h,'Efectivo',CURRENT_TIMESTAMP)"""), {"t": tipo, "c": categoria, "x": concepto, "m": monto, "h": hoy})
    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        ejecutar()
        print("Importes demo ajustados a un escenario realista.")
