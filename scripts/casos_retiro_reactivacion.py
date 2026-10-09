"""Crea casos idempotentes para validar retiro y reactivación de alumnos."""
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from app import create_app
from app.extensions import db
from app.models import (
    Alumno, Auditoria, Categoria, Configuracion, HistorialAlumno, Pago,
)
from app.utils.backup import crear_respaldo


CI_RETIRADO = "CASO-RETIRO-001"
CI_REACTIVADO = "CASO-REACTIVADO-001"


def _categoria_y_nacimiento():
    categoria = (
        Categoria.query
        .filter(Categoria.edad_min.is_not(None))
        .order_by(Categoria.edad_min)
        .first()
    )
    if categoria is None:
        raise RuntimeError("No existe una categoría con rango de edad.")
    edad = categoria.edad_min
    return categoria, date.today() - relativedelta(years=edad)


def _agregar_pago(alumno, fecha_pago, monto, modo):
    mes = fecha_pago.strftime("%Y-%m")
    existente = Pago.query.filter_by(
        id_alumno=alumno.id_alumno, mes_pagado=mes, eliminado_en=None
    ).first()
    if existente:
        return existente
    pago = Pago(
        alumno=alumno,
        fecha_pago=fecha_pago,
        fecha_vencimiento=fecha_pago + relativedelta(months=1),
        mes_pagado=mes,
        modo_pago=modo,
        monto=monto,
    )
    db.session.add(pago)
    return pago


def crear_casos():
    hoy = date.today()
    categoria, nacimiento = _categoria_y_nacimiento()
    monto = Decimal(Configuracion.obtener().monto_mensualidad or 100)
    creados = []

    retirado = Alumno.query.filter_by(ci=CI_RETIRADO).first()
    if retirado is None:
        fecha_retiro = hoy - timedelta(days=20)
        fecha_pago = hoy - timedelta(days=50)
        retirado = Alumno(
            nombre="Caso",
            apellido="Alumno Retirado",
            ci=CI_RETIRADO,
            fecha_nacimiento=nacimiento,
            categoria=categoria,
            categoria_manual=True,
            estado="Retirado",
            fecha_base_pago=fecha_pago,
            fecha_retiro=fecha_retiro,
            tutor="Registro de validación",
        )
        db.session.add(retirado)
        db.session.flush()
        _agregar_pago(retirado, fecha_pago, monto, "Efectivo")
        db.session.add(HistorialAlumno(
            alumno=retirado,
            tipo="retiro",
            valor_anterior="Activo",
            valor_nuevo=fecha_retiro.isoformat(),
            motivo="Caso controlado: alumno retirado para validación.",
        ))
        db.session.add(Auditoria(
            modulo="Alumnos", accion="Crear caso de retiro",
            entidad="Alumno", id_entidad=retirado.id_alumno,
            detalle=CI_RETIRADO,
        ))
        creados.append(retirado)

    reactivado = Alumno.query.filter_by(ci=CI_REACTIVADO).first()
    if reactivado is None:
        fecha_retiro = hoy - timedelta(days=70)
        fecha_reactivacion = hoy - timedelta(days=15)
        pago_anterior = hoy - timedelta(days=100)
        reactivado = Alumno(
            nombre="Caso",
            apellido="Alumno Reactivado",
            ci=CI_REACTIVADO,
            fecha_nacimiento=nacimiento,
            categoria=categoria,
            categoria_manual=True,
            estado="Activo",
            fecha_base_pago=fecha_reactivacion,
            fecha_retiro=fecha_retiro,
            fecha_ultima_reactivacion=fecha_reactivacion,
            tutor="Registro de validación",
        )
        db.session.add(reactivado)
        db.session.flush()
        _agregar_pago(reactivado, pago_anterior, monto, "Efectivo")
        _agregar_pago(reactivado, fecha_reactivacion, monto, "QR")
        db.session.add_all([
            HistorialAlumno(
                alumno=reactivado,
                tipo="retiro",
                valor_anterior="Activo",
                valor_nuevo=fecha_retiro.isoformat(),
                motivo="Caso controlado: retiro previo a reactivación.",
            ),
            HistorialAlumno(
                alumno=reactivado,
                tipo="reactivacion",
                valor_anterior=fecha_retiro.isoformat(),
                valor_nuevo=fecha_reactivacion.isoformat(),
                motivo="Caso controlado: alumno que volvió a la academia.",
            ),
        ])
        db.session.add(Auditoria(
            modulo="Alumnos", accion="Crear caso de reactivación",
            entidad="Alumno", id_entidad=reactivado.id_alumno,
            detalle=CI_REACTIVADO,
        ))
        creados.append(reactivado)

    db.session.commit()
    return creados, retirado, reactivado


def main():
    app = create_app()
    with app.app_context():
        respaldo = crear_respaldo(app, "antes_casos_retiro_reactivacion")
        creados, retirado, reactivado = crear_casos()
        print(f"Respaldo previo: {respaldo}")
        print(f"Casos nuevos: {len(creados)}")
        print(
            f"Retirado: {retirado.codigo_interno} | {retirado.ci} | "
            f"estado={retirado.estado}"
        )
        print(
            f"Reactivado: {reactivado.codigo_interno} | {reactivado.ci} | "
            f"estado={reactivado.estado} | "
            f"reactivación={reactivado.fecha_ultima_reactivacion}"
        )


if __name__ == "__main__":
    main()
