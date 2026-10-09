from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models import (
    Alumno, BecaHistorial, Categoria, HistorialCategoriaAlumno,
    InscripcionGestion, Tarifa,
)
from app.utils.reglas import calcular_monto_pago


def test_inscripcion_e_historial_conservan_snapshot_de_gestion(app):
    categoria = Categoria.query.filter_by(nombre="13").first()
    alumno = Alumno(nombre="Ciclo", apellido="Histórico", fecha_nacimiento=date(2013, 1, 1))
    db.session.add(alumno)
    db.session.flush()
    db.session.add(InscripcionGestion(
        id_alumno=alumno.id_alumno, gestion=2026, fecha_inscripcion=date(2026, 1, 10),
        estado="Activa", id_categoria=categoria.id_categoria,
        monto_tarifa=Decimal("130.00"), porcentaje_beca=Decimal("25.00"),
    ))
    db.session.add(HistorialCategoriaAlumno(
        id_alumno=alumno.id_alumno, id_categoria=categoria.id_categoria,
        fecha_inicio=date(2026, 1, 10), tipo_asignacion="Manual",
    ))
    db.session.commit()
    assert alumno.inscripciones[0].monto_tarifa == Decimal("130.00")
    assert alumno.historial_categorias[0].categoria.nombre == "13"


def test_tarifa_y_beca_se_resuelven_por_vigencia(app):
    categoria = Categoria.query.filter_by(nombre="13").first()
    alumno = Alumno(
        nombre="Tarifa", apellido="Vigente", fecha_nacimiento=date(2013, 1, 1),
        id_categoria=categoria.id_categoria, beca="Ninguna",
    )
    db.session.add_all([
        alumno,
        Tarifa(concepto="Mensualidad", monto=Decimal("200.00"),
               fecha_inicio=date(2026, 1, 1), id_categoria=categoria.id_categoria),
    ])
    db.session.flush()
    db.session.add(BecaHistorial(
        id_alumno=alumno.id_alumno, porcentaje=Decimal("25.00"),
        fecha_inicio=date(2026, 1, 1), estado="Activa",
    ))
    db.session.commit()
    assert calcular_monto_pago(alumno, False, "2026-08") == Decimal("150.00")

