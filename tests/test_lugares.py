from app.extensions import db
from app.models import Categoria, Equipo, EventoAgenda, Lugar, Partido


def test_registrar_lugar_y_mostrarlo_en_programaciones(client):
    respuesta = client.post(
        "/lugares/nuevo",
        data={
            "nombre": "Cancha Norte",
            "tipo": "Cancha",
            "direccion": "Zona Norte",
            "google_maps_url": "https://maps.app.goo.gl/CanchaNorte123",
            "activo": "1",
        },
    )
    assert respuesta.status_code == 302
    lugar = Lugar.query.filter_by(nombre="Cancha Norte").one()
    assert lugar.activo is True
    assert lugar.google_maps_url == "https://maps.app.goo.gl/CanchaNorte123"

    for ruta in (
        "/partidos/nuevo",
        "/agenda/nuevo",
        "/calendario/entrenamientos/nuevo",
        "/campeonatos/nuevo",
    ):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200
        assert b"Cancha Norte" in respuesta.data

    respuesta = client.post(
        "/agenda/nuevo",
        data={
            "fecha": "2026-07-25",
            "hora": "15:00",
            "descripcion": "Prueba de mapa",
            "lugar": "Cancha Norte",
        },
    )
    assert respuesta.status_code == 302
    evento = EventoAgenda.query.filter_by(descripcion="Prueba de mapa").one()
    assert evento.id_lugar == lugar.id_lugar
    assert b"https://maps.app.goo.gl/CanchaNorte123" in client.get("/agenda/").data
    assert b"https://maps.app.goo.gl/CanchaNorte123" in client.get(
        "/calendario/?anio=2026&mes=7"
    ).data

    categoria = Categoria.query.first()
    equipo = Equipo(nombre="Equipo del mapa", categoria=categoria, es_rival=False)
    db.session.add(equipo)
    db.session.commit()
    respuesta = client.post(
        "/partidos/nuevo",
        data={
            "fecha": "2026-07-26",
            "hora": "10:00",
            "rival": "Visitante de prueba",
            "cancha": "Cancha Norte",
            "id_equipo": equipo.id_equipo,
            "id_categoria": categoria.id_categoria,
        },
    )
    assert respuesta.status_code == 302
    partido = Partido.query.filter_by(rival="Visitante de prueba").one()
    assert partido.id_lugar == lugar.id_lugar
    assert b"https://maps.app.goo.gl/CanchaNorte123" in client.get("/partidos/").data


def test_rechaza_enlace_que_no_es_de_google_maps(client):
    respuesta = client.post(
        "/lugares/nuevo",
        data={
            "nombre": "Cancha enlace inválido",
            "tipo": "Cancha",
            "google_maps_url": "https://sitio-ejemplo.test/ubicacion",
            "activo": "1",
        },
    )
    assert respuesta.status_code == 200
    assert Lugar.query.filter_by(nombre="Cancha enlace inválido").first() is None


def test_no_permite_nombres_de_lugar_duplicados(client):
    db.session.add(Lugar(nombre="Estadio Central", tipo="Cancha", activo=True))
    db.session.commit()
    respuesta = client.post(
        "/lugares/nuevo",
        data={
            "nombre": "estadio central",
            "tipo": "Lugar",
            "activo": "1",
        },
    )
    assert respuesta.status_code == 200
    assert Lugar.query.count() == 1
