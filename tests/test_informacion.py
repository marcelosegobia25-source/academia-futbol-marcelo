from datetime import date, datetime, timedelta
import hashlib
import json
import sqlite3
import zipfile
from io import BytesIO

from app.extensions import db
from app.models import Alumno, Categoria, Equipo, Pago
from app.utils.resumen_categorias import construir_resumen_categorias


def test_informacion_general_cuenta_alumno_una_sola_vez(client, app):
    with app.app_context():
        categoria = Categoria.query.first()
        equipo_a = Equipo(nombre="Equipo A", categoria=categoria)
        equipo_b = Equipo(nombre="Equipo B", categoria=categoria)
        alumno = Alumno(
            nombre="Ana",
            apellido="Prueba",
            fecha_nacimiento=date(2014, 1, 1),
            estado="Activo",
            categoria=categoria,
            equipos=[equipo_a, equipo_b],
        )
        db.session.add(alumno)
        db.session.commit()

    respuesta = client.get("/informacion/")
    assert respuesta.status_code == 200
    assert b"Jugadores activos" in respuesta.data
    assert b"Equipo A" in respuesta.data
    assert b"Equipo B" in respuesta.data
    assert b"descargarRespaldoCompleto(event, this)" in respuesta.data
    assert b'id="ultimo-respaldo-completo"' in respuesta.data


def test_equipo_general_aparece_en_cada_categoria_con_su_conteo(client, app):
    with app.app_context():
        categorias = Categoria.query.limit(2).all()
        equipo = Equipo(nombre="Equipo General")
        alumnos = [
            Alumno(
                nombre=f"Alumno {indice}",
                apellido="General",
                fecha_nacimiento=date(2014, 1, 1),
                estado="Activo",
                categoria=categoria,
                equipos=[equipo],
            )
            for indice, categoria in enumerate(categorias, start=1)
        ]
        db.session.add_all(alumnos)
        db.session.commit()

    respuesta = client.get("/informacion/")
    assert respuesta.status_code == 200
    with app.app_context():
        cantidad_categorias = Categoria.query.count()
    # Una vez dentro de cada categoría y una vez en el resumen general
    # independiente de equipos.
    assert respuesta.data.count(b"Equipo General") == cantidad_categorias + 1


def test_informacion_general_muestra_estado_vencido(client, app):
    with app.app_context():
        categoria = Categoria.query.first()
        alumno = Alumno(
            nombre="Luis",
            apellido="Vencido",
            fecha_nacimiento=date(2013, 1, 1),
            estado="Activo",
            categoria=categoria,
        )
        db.session.add(alumno)
        db.session.flush()
        db.session.add(Pago(
            alumno=alumno,
            fecha_pago=date.today() - timedelta(days=60),
            fecha_vencimiento=date.today() - timedelta(days=30),
            mes_pagado=(date.today() - timedelta(days=60)).strftime("%Y-%m"),
            modo_pago="Efectivo",
            monto=100,
        ))
        db.session.commit()

    respuesta = client.get("/informacion/")
    assert respuesta.status_code == 200
    assert b"Vencidos" in respuesta.data


def test_recaudacion_mes_se_actualiza_y_conserva_pagos_de_retirados(client, app):
    with app.app_context():
        categoria = Categoria.query.first()
        alumnos = [
            Alumno(
                nombre=f"Recaudacion {indice}",
                apellido="Prueba",
                fecha_nacimiento=date(2014, 1, 1),
                estado=estado,
                categoria=categoria,
            )
            for indice, estado in enumerate(
                ("Activo", "Retirado", "Activo", "Activo"), start=1
            )
        ]
        db.session.add_all(alumnos)
        db.session.flush()
        hoy = date.today()
        pagos = [
            Pago(
                alumno=alumnos[0], fecha_pago=hoy,
                fecha_vencimiento=hoy + timedelta(days=30),
                mes_pagado=f"{hoy.year}-01", modo_pago="Efectivo", monto=100,
            ),
            Pago(
                alumno=alumnos[1], fecha_pago=hoy,
                fecha_vencimiento=hoy + timedelta(days=30),
                mes_pagado=f"{hoy.year}-02", modo_pago="QR", monto=75,
            ),
            Pago(
                alumno=alumnos[2], fecha_pago=hoy,
                fecha_vencimiento=hoy + timedelta(days=30),
                mes_pagado=f"{hoy.year}-03", modo_pago="Efectivo", monto=50,
                es_beca=True,
            ),
            Pago(
                alumno=alumnos[3], fecha_pago=hoy,
                fecha_vencimiento=hoy + timedelta(days=30),
                mes_pagado=f"{hoy.year}-04", modo_pago="Efectivo", monto=500,
                eliminado_en=datetime.now(),
            ),
        ]
        db.session.add_all(pagos)
        db.session.commit()

    respuesta = client.get("/informacion/recaudacion-mes")
    assert respuesta.status_code == 200
    assert b"Bs 175.00" in respuesta.data
    assert b"Bs 100.00" in respuesta.data
    assert b"Bs 75.00" in respuesta.data
    assert b"3 pagos registrados" in respuesta.data
    assert b'hx-trigger="every 5s"' in respuesta.data


def test_resumen_general_excluye_retirados_de_categoria_y_equipo(app):
    with app.app_context():
        categoria = Categoria.query.first()
        equipo = Equipo(nombre="Solo activos")
        activo = Alumno(
            nombre="Jugador",
            apellido="Activo",
            fecha_nacimiento=date(2014, 1, 1),
            estado="Activo",
            categoria=categoria,
            equipos=[equipo],
        )
        retirado = Alumno(
            nombre="Jugador",
            apellido="Retirado",
            fecha_nacimiento=date(2014, 1, 1),
            estado="Retirado",
            categoria=categoria,
            equipos=[equipo],
        )
        db.session.add_all([activo, retirado])
        db.session.commit()

        resumen = construir_resumen_categorias(
            [categoria], [equipo], [activo, retirado], solo_activos=True
        )[0]
        assert resumen["total"] == 1
        assert resumen["equipos"][0]["total"] == 1


def test_boton_descarga_respaldo_completo_con_base_fotos_y_manifiesto(
    client, app, tmp_path
):
    instancia = tmp_path / "instance"
    fotos = instancia / "uploads" / "alumnos"
    fotos.mkdir(parents=True)
    base = instancia / "academia.db"
    conexion = sqlite3.connect(base)
    conexion.execute("create table verificacion (valor text)")
    conexion.execute("insert into verificacion values ('respaldo correcto')")
    conexion.commit()
    conexion.close()
    foto = fotos / "jugador.png"
    foto.write_bytes(b"foto-de-prueba")

    app.instance_path = str(instancia)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{base}"
    app.config["UPLOAD_FOLDER"] = str(fotos)

    respuesta = client.post("/informacion/respaldo-completo")

    assert respuesta.status_code == 200
    assert respuesta.mimetype == "application/zip"
    assert "academia_completo_" in respuesta.headers["Content-Disposition"]
    with zipfile.ZipFile(BytesIO(respuesta.data)) as paquete:
        assert {"academia.db", "fotos/jugador.png", "manifiesto.json"} <= set(
            paquete.namelist()
        )
        manifiesto = json.loads(paquete.read("manifiesto.json"))
        for nombre, esperado in manifiesto["sha256"].items():
            assert hashlib.sha256(paquete.read(nombre)).hexdigest() == esperado
