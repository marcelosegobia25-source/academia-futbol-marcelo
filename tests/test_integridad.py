from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Alumno, Categoria, Configuracion, Pago
from app.utils.reglas import calcular_monto_pago


def crear_alumno(**cambios):
    datos = {
        "nombre": "Ana",
        "apellido": "Prueba",
        "fecha_nacimiento": date(2014, 5, 10),
        "estado": "Activo",
        "beca": "Ninguna",
    }
    datos.update(cambios)
    alumno = Alumno(**datos)
    db.session.add(alumno)
    db.session.commit()
    return alumno


def test_sqlite_activa_claves_foraneas(app):
    assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1
    assert db.session.execute(text("PRAGMA journal_mode")).scalar() in {"memory", "wal"}


def test_servidor_rechaza_rango_categoria_invalido(client):
    respuesta = client.post(
        "/categorias/nuevo",
        data={"nombre": "Inválida", "edad_min": "18", "edad_max": "10"},
    )
    assert respuesta.status_code == 200
    assert Categoria.query.filter_by(nombre="Inválida").first() is None


def test_servidor_rechaza_enumeraciones_manipuladas(client):
    respuesta = client.post(
        "/alumnos/nuevo",
        data={
            "nombre": "Manipulada",
            "apellido": "Prueba",
            "fecha_nacimiento": "2015-01-01",
            "estado": "Estado falso",
            "posicion": "XYZ",
            "pierna_habil": "Otra",
            "sexo": "X",
            "beca": "Gratis",
        },
    )
    assert respuesta.status_code == 200
    assert Alumno.query.filter_by(nombre="Manipulada").first() is None


def test_pagos_parciales_del_mismo_mes_se_permiten(app):
    alumno = crear_alumno()
    primero = Pago(
        id_alumno=alumno.id_alumno,
        fecha_pago=date.today(),
        fecha_vencimiento=date.today() + timedelta(days=30),
        mes_pagado="2026-07",
        modo_pago="Efectivo",
        monto=100,
    )
    db.session.add(primero)
    db.session.commit()
    db.session.add(Pago(
        id_alumno=alumno.id_alumno,
        fecha_pago=date.today(),
        fecha_vencimiento=date.today() + timedelta(days=30),
        mes_pagado="2026-07",
        modo_pago="QR",
        monto=100,
    ))
    db.session.commit()
    assert Pago.query.filter_by(id_alumno=alumno.id_alumno, mes_pagado="2026-07").count() == 2


def test_base_rechaza_stock_negativo_aunque_se_eviten_formularios(app):
    with pytest.raises(IntegrityError):
        db.session.execute(text(
            "INSERT INTO producto(codigo,nombre,categoria,activo,creado_en) "
            "VALUES ('X','Producto','Prueba',1,CURRENT_TIMESTAMP)"
        ))
        id_producto = db.session.execute(text("SELECT id_producto FROM producto WHERE codigo='X'")).scalar()
        db.session.execute(text(
            "INSERT INTO producto_variante(id_producto,talla,color,precio_compra,precio_venta,stock,stock_minimo) "
            "VALUES (:id,'U','N',1,2,-1,0)"
        ), {"id": id_producto})
        db.session.commit()
    db.session.rollback()
    db.session.rollback()


def test_beca_vencida_no_reduce_mensualidad(app):
    Configuracion.obtener().monto_mensualidad = 200
    alumno = crear_alumno(
        beca="Completa", beca_fecha_fin=date.today() - timedelta(days=1)
    )
    assert alumno.beca_vigente == "Ninguna"
    assert calcular_monto_pago(alumno, False) == 200


def test_alumno_retirado_no_puede_pagar(client):
    alumno = crear_alumno(estado="Retirado")
    respuesta = client.post(
        f"/pagos/alumno/{alumno.id_alumno}/nuevo",
        data={
            "mes_pagado": "2026-07",
            "fecha_pago": date.today().isoformat(),
            "modo_pago": "Efectivo",
        },
    )
    assert respuesta.status_code == 302
    assert Pago.query.count() == 0
