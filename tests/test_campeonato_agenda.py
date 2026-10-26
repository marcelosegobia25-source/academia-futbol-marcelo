from datetime import date, time, timedelta
from io import BytesIO

from openpyxl import load_workbook

from app.extensions import db
from app.models import (
    Alumno, AlumnoCampeonato, Campeonato, Categoria, ConflictoAutorizado, Equipo, EventoAgenda,
    Partido, Posicion, Usuario,
)


def preparar_campeonato():
    categoria = Categoria.query.filter_by(nombre="13").first()
    local = Equipo(nombre="Academia A")
    visita = Equipo(nombre="Academia B")
    campeonato = Campeonato(
        nombre="Prueba",
        fecha_inicio=date(2026, 8, 1),
        categorias=[categoria],
        equipos=[local, visita],
    )
    db.session.add_all([local, visita, campeonato])
    db.session.commit()
    return campeonato, categoria, local, visita


def test_fixture_crea_agenda_y_rival_formal(client):
    campeonato, categoria, local, visita = preparar_campeonato()
    respuesta = client.post(f"/campeonatos/{campeonato.id_campeonato}/generar-fixture")
    assert respuesta.status_code == 302
    partido = Partido.query.filter_by(id_campeonato=campeonato.id_campeonato).one()
    assert partido.id_equipo_rival == visita.id_equipo
    assert EventoAgenda.query.filter_by(id_partido=partido.id_partido).count() == 1


def test_conflicto_de_cancha_se_rechaza_y_admin_puede_autorizarlo(client, app):
    categoria = Categoria.query.first()
    equipo_a = Equipo(nombre="Equipo conflicto A", id_categoria=categoria.id_categoria)
    equipo_b = Equipo(nombre="Equipo conflicto B", id_categoria=categoria.id_categoria)
    db.session.add_all([equipo_a, equipo_b]); db.session.commit()
    datos = {"fecha": "2026-09-20", "hora": "16:00", "id_categoria": str(categoria.id_categoria), "cancha": "Cancha Central"}
    client.post("/partidos/nuevo", data={**datos, "id_equipo": str(equipo_a.id_equipo), "rival": "Rival Uno"})
    rechazada = client.post("/partidos/nuevo", data={**datos, "id_equipo": str(equipo_b.id_equipo), "rival": "Rival Dos"})
    assert b"Conflicto de horario" in rechazada.data
    assert Partido.query.count() == 1

    app.config["AUTH_REQUIRED"] = True
    Usuario.query.filter_by(nombre_usuario="admin").one().debe_cambiar_clave = False
    db.session.commit()
    client.post("/acceso/", data={"nombre_usuario": "admin", "contrasena": "00000"})
    autorizada = client.post("/partidos/nuevo", data={
        **datos, "id_equipo": str(equipo_b.id_equipo), "rival": "Rival Dos",
        "autorizar_conflicto": "1", "motivo_conflicto": "Evento especial aprobado",
    })
    assert autorizada.status_code == 302
    assert Partido.query.count() == 2
    assert ConflictoAutorizado.query.count() == 1


def test_corregir_resultado_recalcula_sin_duplicar(client):
    campeonato, categoria, local, visita = preparar_campeonato()
    client.post(f"/campeonatos/{campeonato.id_campeonato}/generar-fixture")
    partido = Partido.query.filter_by(id_campeonato=campeonato.id_campeonato).one()

    client.post(
        f"/campeonatos/partidos/{partido.id_partido}/resultado",
        data={"goles_local": "2", "goles_visita": "0"},
    )
    client.post(
        f"/campeonatos/partidos/{partido.id_partido}/resultado",
        data={
            "goles_local": "1", "goles_visita": "1",
            "motivo_correccion": "Corrección del acta arbitral",
        },
    )

    posiciones = Posicion.query.filter_by(
        id_campeonato=campeonato.id_campeonato
    ).order_by(Posicion.id_equipo).all()
    assert len(posiciones) == 2
    assert all(posicion.pj == 1 for posicion in posiciones)
    assert all(posicion.pe == 1 for posicion in posiciones)
    assert all(posicion.pts == 1 for posicion in posiciones)


def test_regenerar_fixture_no_deja_eventos_huerfanos(client):
    campeonato, categoria, local, visita = preparar_campeonato()
    client.post(f"/campeonatos/{campeonato.id_campeonato}/generar-fixture")
    client.post(f"/campeonatos/{campeonato.id_campeonato}/generar-fixture")
    assert Partido.query.filter_by(id_campeonato=campeonato.id_campeonato).count() == 1
    assert EventoAgenda.query.filter_by(tipo="Partido").count() == 1


def test_registrar_rival_y_generar_fixture(client):
    categoria = Categoria.query.filter_by(nombre="11").first()
    respuesta = client.post(
        "/campeonatos/rivales/nuevo",
        data={"nombre": "Deportivo Norte", "id_categoria": categoria.id_categoria},
    )
    assert respuesta.status_code == 302
    rival = Equipo.query.filter_by(
        nombre="Deportivo Norte", es_rival=True
    ).one()

    local = Equipo(nombre="Academia Sub 11", es_rival=False)
    campeonato = Campeonato(
        nombre="Copa Sub 11",
        fecha_inicio=date(2026, 9, 1),
        categorias=[categoria],
        equipos=[local, rival],
    )
    db.session.add_all([local, campeonato])
    db.session.commit()

    respuesta = client.post(
        f"/campeonatos/{campeonato.id_campeonato}/generar-fixture"
    )
    assert respuesta.status_code == 302
    partido = Partido.query.filter_by(
        id_campeonato=campeonato.id_campeonato
    ).one()
    assert partido.equipo.nombre == "Academia Sub 11"
    assert partido.equipo_rival.nombre == "Deportivo Norte"
    assert Posicion.query.filter_by(
        id_campeonato=campeonato.id_campeonato
    ).count() == 2


def test_rival_no_aparece_como_equipo_asignable(client):
    categoria = Categoria.query.filter_by(nombre="13").first()
    db.session.add(Equipo(
        nombre="Rival oculto",
        categoria=categoria,
        es_rival=True,
    ))
    db.session.commit()

    assert b"Rival oculto" not in client.get("/equipos/").data
    assert b"Rival oculto" not in client.get("/alumnos/nuevo").data
    assert b"Rival oculto" in client.get("/campeonatos/rivales").data


def test_rival_general_funciona_en_cualquier_categoria(client):
    respuesta = client.post(
        "/campeonatos/rivales/nuevo",
        data={"nombre": "Rival General", "id_categoria": ""},
    )
    assert respuesta.status_code == 302
    rival = Equipo.query.filter_by(
        nombre="Rival General", es_rival=True
    ).one()
    assert rival.id_categoria is None

    pagina = client.get("/campeonatos/rivales")
    assert pagina.status_code == 200
    assert b"Todas las categor" in pagina.data


def test_partido_manual_se_puede_crear_y_editar(client):
    campeonato, categoria, local, visita = preparar_campeonato()
    assert client.get(
        f"/campeonatos/{campeonato.id_campeonato}"
    ).status_code == 200
    pagina_formulario = client.get(
        f"/campeonatos/{campeonato.id_campeonato}/partidos/nuevo"
    )
    assert pagina_formulario.status_code == 200
    assert b"Fixture manual" in pagina_formulario.data
    respuesta = client.post(
        f"/campeonatos/{campeonato.id_campeonato}/partidos/nuevo",
        data={
            "id_categoria": categoria.id_categoria,
            "id_equipo": local.id_equipo,
            "id_equipo_rival": visita.id_equipo,
            "fase": "Semifinal",
            "jornada": "2",
            "orden_llave": "1",
            "fecha": "2026-08-08",
            "hora": "10:30",
            "cancha": "Cancha central",
            "estado_partido": "Programado",
        },
    )
    assert respuesta.status_code == 302
    partido = Partido.query.filter_by(id_campeonato=campeonato.id_campeonato).one()
    assert partido.fase == "Semifinal"
    assert partido.jornada == 2
    assert EventoAgenda.query.filter_by(id_partido=partido.id_partido).count() == 1

    client.post(
        f"/campeonatos/{campeonato.id_campeonato}/partidos/{partido.id_partido}/editar",
        data={
            "id_categoria": categoria.id_categoria,
            "id_equipo": visita.id_equipo,
            "id_equipo_rival": local.id_equipo,
            "fase": "Final",
            "jornada": "3",
            "orden_llave": "1",
            "fecha": "2026-08-15",
            "estado_partido": "Reprogramado",
        },
    )
    assert partido.fase == "Final"
    assert partido.id_equipo == visita.id_equipo
    assert partido.estado_partido == "Reprogramado"


def test_editar_solamente_hora_actualiza_partido_y_agenda(client):
    campeonato, categoria, local, visita = preparar_campeonato()
    client.post(
        f"/campeonatos/{campeonato.id_campeonato}/partidos/nuevo",
        data={
            "id_categoria": categoria.id_categoria,
            "id_equipo": local.id_equipo,
            "id_equipo_rival": visita.id_equipo,
            "fase": "Liga",
            "jornada": "1",
            "fecha": "2026-08-08",
            "hora": "10:30",
            "cancha": "Cancha central",
            "estado_partido": "Programado",
        },
    )
    partido = Partido.query.filter_by(id_campeonato=campeonato.id_campeonato).one()

    respuesta = client.post(
        f"/campeonatos/{campeonato.id_campeonato}/partidos/{partido.id_partido}/editar",
        data={
            "id_categoria": categoria.id_categoria,
            "id_equipo": local.id_equipo,
            "id_equipo_rival": visita.id_equipo,
            "fase": "Liga",
            "jornada": "1",
            "fecha": "2026-08-08",
            "hora": "18:45",
            "cancha": "Cancha central",
            "estado_partido": "Programado",
        },
    )

    assert respuesta.status_code == 302
    db.session.refresh(partido)
    evento = EventoAgenda.query.filter_by(id_partido=partido.id_partido).one()
    assert partido.hora == time(18, 45)
    assert evento.hora == time(18, 45)


def test_fixture_pone_futuros_antes_de_pasados_en_pantalla_y_exportacion(client):
    campeonato, categoria, local, visita = preparar_campeonato()
    hoy = date.today()
    pasado = Partido(
        fecha=hoy - timedelta(days=2), hora=time(9), id_equipo=local.id_equipo,
        id_equipo_rival=visita.id_equipo, id_categoria=categoria.id_categoria,
        rival=visita.nombre, id_campeonato=campeonato.id_campeonato,
    )
    futuro = Partido(
        fecha=hoy + timedelta(days=2), hora=time(10), id_equipo=local.id_equipo,
        id_equipo_rival=visita.id_equipo, id_categoria=categoria.id_categoria,
        rival=visita.nombre, id_campeonato=campeonato.id_campeonato,
    )
    db.session.add_all([pasado, futuro])
    db.session.commit()

    pagina = client.get(f"/campeonatos/{campeonato.id_campeonato}").data
    # Limitar la comprobación al cuerpo de la tabla. La fecha de un partido
    # puede coincidir con la fecha de inicio mostrada antes del fixture.
    cuerpo_fixture = pagina.split(b"<tbody>", 1)[1].split(b"</tbody>", 1)[0]
    fecha_futura = futuro.fecha.strftime("%d/%m/%Y").encode()
    fecha_pasada = pasado.fecha.strftime("%d/%m/%Y").encode()
    assert cuerpo_fixture.find(fecha_futura) < cuerpo_fixture.find(fecha_pasada)

    respuesta = client.get(f"/campeonatos/{campeonato.id_campeonato}/fixture.xlsx")
    filas = list(load_workbook(BytesIO(respuesta.data)).active.values)
    assert filas[1][4] == futuro.fecha.strftime("%d/%m/%Y")
    assert filas[2][4] == pasado.fecha.strftime("%d/%m/%Y")


def test_eliminatoria_exige_desempate_y_avanza_ganadores(client):
    categoria = Categoria.query.filter_by(nombre="13").first()
    equipos = [Equipo(nombre=f"Equipo {n}") for n in range(1, 5)]
    campeonato = Campeonato(
        nombre="Copa eliminación", fecha_inicio=date(2026, 8, 1),
        categorias=[categoria], equipos=equipos, clasificados=4,
    )
    db.session.add(campeonato)
    db.session.commit()
    for equipo in equipos:
        db.session.add(Posicion(
            id_campeonato=campeonato.id_campeonato,
            id_categoria=categoria.id_categoria,
            id_equipo=equipo.id_equipo,
        ))
    db.session.commit()
    client.post(
        f"/campeonatos/{campeonato.id_campeonato}/eliminatorias/generar",
        data={"id_categoria": categoria.id_categoria},
    )
    semifinales = Partido.query.filter_by(
        id_campeonato=campeonato.id_campeonato, fase="Semifinal"
    ).order_by(Partido.orden_llave).all()
    assert len(semifinales) == 2

    respuesta = client.post(
        f"/campeonatos/partidos/{semifinales[0].id_partido}/resultado",
        data={"goles_local": "1", "goles_visita": "1"},
    )
    assert respuesta.status_code == 302
    assert semifinales[0].estado_partido == "Programado"

    client.post(
        f"/campeonatos/partidos/{semifinales[0].id_partido}/resultado",
        data={"goles_local": "1", "goles_visita": "1", "penales_local": "4", "penales_visita": "3"},
    )
    client.post(
        f"/campeonatos/partidos/{semifinales[1].id_partido}/resultado",
        data={"goles_local": "2", "goles_visita": "0"},
    )
    final = Partido.query.filter_by(
        id_campeonato=campeonato.id_campeonato, fase="Final"
    ).one()
    assert final.id_equipo is not None
    assert final.id_equipo_rival is not None


def test_finalizar_archiva_y_reabrir_restaura_convocatoria(client):
    campeonato, categoria, local, visita = preparar_campeonato()
    alumno = Alumno(
        nombre="Ana", apellido="Prueba", fecha_nacimiento=date(2013, 1, 1),
        ci="990015", id_categoria=categoria.id_categoria, estado="Activo",
    )
    db.session.add(alumno)
    db.session.flush()
    convocatoria = AlumnoCampeonato(
        id_campeonato=campeonato.id_campeonato,
        id_alumno=alumno.id_alumno, habilitado=True,
    )
    db.session.add(convocatoria)
    db.session.commit()

    client.post(
        f"/campeonatos/{campeonato.id_campeonato}/finalizar",
        data={"forzar": "1", "sin_campeon": "1", "motivo": "Concluido sin campeón"},
    )
    assert campeonato.estado == "Finalizado"
    assert convocatoria.archivado is True
    assert convocatoria.habilitado is False

    client.post(
        f"/campeonatos/{campeonato.id_campeonato}/reabrir",
        data={"motivo": "Corrección administrativa"},
    )
    assert campeonato.estado == "En curso"
    assert convocatoria.archivado is False
    assert convocatoria.habilitado is True
