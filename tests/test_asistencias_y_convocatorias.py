from datetime import date
from app.extensions import db
from app.models import Categoria, Alumno, Convocatoria, DetalleConvocatoria, SesionEntrenamiento, AsistenciaEntrenamiento


def test_asistencias_vistas_principales(client):
    r1 = client.get("/alumnos/asistencias?tab=tomar")
    assert r1.status_code == 200
    assert "Tomar Asistencia".encode("utf-8") in r1.data

    r2 = client.get("/alumnos/asistencias?tab=convocatoria")
    assert r2.status_code == 200
    assert "Nueva Convocatoria".encode("utf-8") in r2.data

    r3 = client.get("/alumnos/asistencias?tab=convocatorias")
    assert r3.status_code == 200
    assert "Convocatorias Guardadas".encode("utf-8") in r3.data

    r4 = client.get("/alumnos/asistencias?tab=historial")
    assert r4.status_code == 200


def _asegurar_datos_prueba():
    cat = Categoria.query.filter_by(nombre="7").first() or Categoria.query.first()
    if not cat:
        cat = Categoria(nombre="7", edad_min=6, edad_max=7)
        db.session.add(cat)
        db.session.commit()

    alumnos = Alumno.query.filter_by(id_categoria=cat.id_categoria, estado="Activo").all()
    if len(alumnos) < 3:
        for i in range(len(alumnos), 3):
            a = Alumno(
                nombre=f"Alumno{i+1}",
                apellido=f"Prueba{i+1}",
                id_categoria=cat.id_categoria,
                fecha_nacimiento=date(2018, 1, 1),
                estado="Activo",
                ci=f"1000000{i+1}",
            )
            db.session.add(a)
        db.session.commit()
    return cat


def test_tomar_asistencia_categoria_restringida(app, client):
    with app.app_context():
        cat1 = _asegurar_datos_prueba()
        alumnos_cat1 = Alumno.query.filter_by(id_categoria=cat1.id_categoria, estado="Activo").all()

        # Filtrar vista para cat1
        resp = client.get(f"/alumnos/asistencias?tab=tomar&id_categoria={cat1.id_categoria}")
        assert resp.status_code == 200
        for a in alumnos_cat1:
            assert a.nombre.encode("utf-8") in resp.data

        # Guardar asistencia
        form_data = {
            "id_categoria": cat1.id_categoria,
            "fecha": date.today().isoformat(),
            "hora": "16:30",
            "lugar": "Cancha 2",
            "observacion_general": "Entrenamiento técnico de prueba",
        }
        for idx, a in enumerate(alumnos_cat1):
            form_data[f"estado_{a.id_alumno}"] = "Presente" if idx % 2 == 0 else "Tarde"
            form_data[f"justificacion_{a.id_alumno}"] = "Nota de test"

        resp_post = client.post("/alumnos/asistencias/guardar", data=form_data, follow_redirects=True)
        assert resp_post.status_code == 200
        assert "registrada correctamente".encode("utf-8") in resp_post.data

        # Verificar que se crearon los registros en BD
        sesion = SesionEntrenamiento.query.filter_by(fecha=date.today()).first()
        assert sesion is not None
        asistencias_sesion = AsistenciaEntrenamiento.query.filter_by(id_sesion_entrenamiento=sesion.id_sesion_entrenamiento).all()
        assert len(asistencias_sesion) >= len(alumnos_cat1)


def test_convocatoria_flujo_completo(app, client):
    with app.app_context():
        cat = _asegurar_datos_prueba()
        alumnos = Alumno.query.filter_by(id_categoria=cat.id_categoria, estado="Activo").limit(3).all()
        ids_convocados = [str(a.id_alumno) for a in alumnos]

        # 1. Crear convocatoria
        post_data = {
            "id_categoria": cat.id_categoria,
            "titulo": "Clásico Interdepartamental Test",
            "fecha": "2026-11-05",
            "hora": "10:00",
            "lugar": "Estadio Félix Capriles",
            "rival": "Rival FC",
            "indicaciones": "Presentarse 45 min antes con uniforme completo",
            "convocados": ids_convocados,
        }
        for idx, a_id in enumerate(ids_convocados, 1):
            post_data[f"rol_{a_id}"] = "Titular" if idx <= 2 else "Suplente"
            post_data[f"dorsal_{a_id}"] = str(idx)
            post_data[f"posicion_{a_id}"] = "Delantero"
            post_data[f"nota_{a_id}"] = "Capitán" if idx == 1 else ""

        resp_guardar = client.post("/alumnos/asistencias/convocatoria/guardar", data=post_data, follow_redirects=True)
        assert resp_guardar.status_code == 200
        assert "Clásico Interdepartamental Test".encode("utf-8") in resp_guardar.data

        conv = Convocatoria.query.filter_by(titulo="Clásico Interdepartamental Test").first()
        assert conv is not None
        assert conv.total_convocados == len(ids_convocados)
        assert len(conv.titulares) == 2
        assert len(conv.suplentes) == 1

        # 2. Ver detalle
        resp_detalle = client.get(f"/alumnos/asistencias/convocatoria/{conv.id_convocatoria}")
        assert resp_detalle.status_code == 200
        assert b"Alineaci\xc3\xb3n Titular" in resp_detalle.data
        assert b"btn-copiar-whatsapp" in resp_detalle.data

        # 3. Exportar PDF
        resp_pdf = client.get(f"/alumnos/asistencias/convocatoria/{conv.id_convocatoria}/pdf")
        assert resp_pdf.status_code == 200
        assert resp_pdf.content_type == "application/pdf"

        # 4. Exportar Excel
        resp_excel = client.get(f"/alumnos/asistencias/convocatoria/{conv.id_convocatoria}/excel")
        assert resp_excel.status_code == 200
        assert "spreadsheetml" in resp_excel.content_type

        # 5. Eliminar convocatoria
        resp_del = client.post(f"/alumnos/asistencias/convocatoria/{conv.id_convocatoria}/eliminar", follow_redirects=True)
        assert resp_del.status_code == 200
        assert Convocatoria.query.filter_by(id_convocatoria=conv.id_convocatoria).first() is None
