"""Crea cinco alumnos retirados para practicar su reactivación manual."""

from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from app import create_app
from app.extensions import db
from app.models import Alumno, Auditoria, Categoria, Configuracion, HistorialAlumno, Pago
from app.utils.backup import crear_respaldo


PREFIJO_CI = "CASO-RETORNO-"


def crear_casos():
    hoy = date.today()
    fecha_pago = hoy - relativedelta(months=6)
    categoria = (
        Categoria.query
        .filter(Categoria.edad_min.is_not(None))
        .order_by(Categoria.edad_min)
        .first()
    )
    if categoria is None:
        raise RuntimeError("No existe una categoría con rango de edad.")

    nacimiento = hoy - relativedelta(years=categoria.edad_min)
    monto = Decimal(Configuracion.obtener().monto_mensualidad or 100)
    creados = []

    for meses_retirado in range(5, 0, -1):
        numero = 6 - meses_retirado
        ci = f"{PREFIJO_CI}{numero:02d}"
        if Alumno.query.filter_by(ci=ci).first() is not None:
            continue

        fecha_retiro = hoy - relativedelta(months=meses_retirado)
        alumno = Alumno(
            nombre=f"Retorno {numero}",
            apellido="Caso de prueba",
            ci=ci,
            fecha_nacimiento=nacimiento,
            categoria=categoria,
            categoria_manual=True,
            estado="Retirado",
            fecha_base_pago=fecha_pago,
            fecha_retiro=fecha_retiro,
            tutor="Caso para reactivación manual",
        )
        db.session.add(alumno)
        db.session.flush()

        db.session.add(Pago(
            alumno=alumno,
            fecha_pago=fecha_pago,
            fecha_vencimiento=fecha_pago + relativedelta(months=1),
            mes_pagado=fecha_pago.strftime("%Y-%m"),
            modo_pago="Efectivo" if numero % 2 else "QR",
            monto=monto,
            numero_operacion=f"PRUEBA-RETORNO-{numero:02d}" if numero % 2 == 0 else None,
        ))
        db.session.add(HistorialAlumno(
            alumno=alumno,
            tipo="retiro",
            valor_anterior="Activo",
            valor_nuevo=fecha_retiro.isoformat(),
            motivo=f"Caso de prueba: retiro hace {meses_retirado} mes(es).",
        ))
        db.session.add(Auditoria(
            modulo="Alumnos",
            accion="Crear caso de retorno",
            entidad="Alumno",
            id_entidad=alumno.id_alumno,
            detalle=f"{ci}; pago={fecha_pago}; retiro={fecha_retiro}",
        ))
        creados.append(alumno)

    db.session.commit()
    return creados


def main():
    app = create_app()
    with app.app_context():
        respaldo = crear_respaldo(app, "antes_cinco_retiros_escalonados")
        creados = crear_casos()
        casos = (
            Alumno.query
            .filter(Alumno.ci.like(f"{PREFIJO_CI}%"))
            .order_by(Alumno.ci)
            .all()
        )
        print(f"RESPALDO={respaldo}")
        print(f"NUEVOS={len(creados)}")
        for alumno in casos:
            pago = alumno.ultimo_pago
            print(
                f"{alumno.codigo_interno}|{alumno.nombre_completo}|{alumno.ci}|"
                f"estado={alumno.estado}|mensualidad={alumno.estado_mensualidad}|"
                f"pago={pago.fecha_pago if pago else '-'}|retiro={alumno.fecha_retiro}"
            )


if __name__ == "__main__":
    main()
