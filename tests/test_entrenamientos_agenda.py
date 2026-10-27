from datetime import date, time, timedelta
from app.extensions import db
from app.models import (
    Entrenamiento, SesionEntrenamiento, AsistenciaEntrenamiento,
    Categoria, Equipo, Lugar, Auditoria, PersonalDeportivo, EventoAgenda,
)
from app.utils.tiempo import hoy_bolivia


def test_crear_entrenamiento_multiples_dias(client):
    cat = Categoria.query.first()
    lugar = Lugar.query.first()
    datos = {
        "dias_semana": ["0", "2", "4"],  # Lunes, Miércoles, Viernes
        "hora_inicio": "15:30",
        "hora_fin": "17:00",
        "id_categoria": str(cat.id_categoria) if cat else "",
        "lugar": lugar.nombre if lugar else "Cancha Principal",
        "activo": "1",
    }
    resp = client.post("/calendario/entrenamientos/nuevo", data=datos, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Entrenamiento(s) fijos agregados correctamente" in resp.data

    # Check 3 records created for days 0, 2, 4
    entrenamientos = Entrenamiento.query.filter_by(hora_inicio=time(15, 30)).all()
    dias_creados = sorted([e.dia_semana for e in entrenamientos])
    assert dias_creados == [0, 2, 4]

    # Verify audit
    auditorias = Auditoria.query.filter_by(modulo="Calendario", accion="Crear entrenamiento").all()
    assert len(auditorias) >= 3


def test_eliminar_entrenamiento_con_sesiones_y_asistencia(client):
    # Create an entrenamiento
    cat = Categoria.query.first()
    e = Entrenamiento(
        dia_semana=1,  # Martes
        hora_inicio=time(18, 0),
        hora_fin=time(19, 30),
        id_categoria=cat.id_categoria if cat else None,
        activo=True,
    )
    db.session.add(e)
    db.session.flush()

    # Create associated session and attendance
    sesion = SesionEntrenamiento(id_entrenamiento=e.id_entrenamiento, fecha=date(2026, 10, 20))
    db.session.add(sesion)
    db.session.flush()

    from app.models import Alumno
    alumno = Alumno.query.first()
    if alumno:
        asistencia = AsistenciaEntrenamiento(
            id_sesion_entrenamiento=sesion.id_sesion_entrenamiento,
            id_alumno=alumno.id_alumno,
            estado="Presente",
        )
        db.session.add(asistencia)
    db.session.commit()

    id_e = e.id_entrenamiento
    id_s = sesion.id_sesion_entrenamiento

    # Delete should NOT fail with FK restriction
    resp = client.post(f"/calendario/entrenamientos/{id_e}/eliminar", follow_redirects=True)
    assert resp.status_code == 200
    assert b"eliminados correctamente" in resp.data

    # Verify deleted
    assert db.session.get(Entrenamiento, id_e) is None
    assert db.session.get(SesionEntrenamiento, id_s) is None

    # Verify audit
    audit = Auditoria.query.filter_by(
        modulo="Calendario", accion="Eliminar entrenamiento", id_entidad=id_e
    ).first()
    assert audit is not None


def test_entrenamiento_se_refleja_en_calendario_y_agenda(client):
    hoy = hoy_bolivia()
    dia_semana_hoy = hoy.weekday()

    # Create an entrenamiento for today's weekday
    e = Entrenamiento(
        dia_semana=dia_semana_hoy,
        hora_inicio=time(14, 0),
        hora_fin=time(15, 30),
        lugar="Estadio de Pruebas",
        activo=True,
    )
    db.session.add(e)
    db.session.commit()

    # 1. Check Calendario view
    res_cal = client.get(f"/calendario/?anio={hoy.year}&mes={hoy.month}")
    assert res_cal.status_code == 200
    assert "Estadio de Pruebas" in res_cal.data.decode("utf-8")
    assert "14:00" in res_cal.data.decode("utf-8")

    # 2. Check Agenda view (filtered by tipo=Entrenamiento)
    res_agenda = client.get("/agenda/?tipo=Entrenamiento")
    assert res_agenda.status_code == 200
    html_agenda = res_agenda.data.decode("utf-8")
    assert "Estadio de Pruebas" in html_agenda
    assert "14:00" in html_agenda
    assert "Entrenamiento" in html_agenda


def test_agenda_filtro_fecha_incluye_entrenamiento(client):
    hoy = hoy_bolivia()
    # Find next Friday
    dias_hasta_viernes = (4 - hoy.weekday()) % 7
    fecha_viernes = hoy + timedelta(days=dias_hasta_viernes)

    e = Entrenamiento(
        dia_semana=4,  # Viernes
        hora_inicio=time(10, 0),
        hora_fin=time(11, 30),
        lugar="Cancha Sintética Viernes",
        activo=True,
    )
    db.session.add(e)
    db.session.commit()

    # Query agenda for that specific Friday
    res = client.get(f"/agenda/?fecha={fecha_viernes.isoformat()}")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Cancha Sintética Viernes" in html
    assert "10:00" in html
