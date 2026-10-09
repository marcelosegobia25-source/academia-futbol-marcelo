from datetime import date, time

from app.extensions import db
from app.models import Alumno, Auditoria, Categoria, Entrenamiento, SesionEntrenamiento


def test_consultar_asistencia_no_crea_sesion_y_guardar_si_audita(client, app):
    with app.app_context():
        categoria = Categoria.query.first()
        alumno = Alumno(nombre="Ana", apellido="Prueba", fecha_nacimiento=date(2014, 1, 1), id_categoria=categoria.id_categoria)
        entrenamiento = Entrenamiento(dia_semana=0, hora_inicio=time(16, 0), id_categoria=categoria.id_categoria)
        db.session.add_all([alumno, entrenamiento]); db.session.commit()
        id_entrenamiento, id_alumno = entrenamiento.id_entrenamiento, alumno.id_alumno

    assert client.get(f"/calendario/entrenamientos/{id_entrenamiento}/asistencia?fecha=2026-08-15").status_code == 200
    with app.app_context():
        assert SesionEntrenamiento.query.count() == 0

    respuesta = client.post(f"/calendario/entrenamientos/{id_entrenamiento}/asistencia", data={
        "fecha": "2026-08-15", f"estado_{id_alumno}": "Presente",
    })
    assert respuesta.status_code == 302
    with app.app_context():
        assert SesionEntrenamiento.query.count() == 1
        assert Auditoria.query.filter_by(modulo="Asistencia", accion="Guardar").count() == 1
