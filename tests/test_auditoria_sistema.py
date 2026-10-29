import io
from datetime import date, time, timedelta
from decimal import Decimal
import pytest

from app.extensions import db
from app.models import (
    Alumno, Categoria, Equipo, Lugar, Pago, Partido, Campeonato,
    Entrenamiento, SesionEntrenamiento, AsistenciaEntrenamiento, Convocatoria,
    Usuario, Rol, Configuracion
)
from app.utils.integridad import auditar_base_datos


def test_auditoria_integridad_base_de_datos(app):
    """Comprueba que la base de datos no tenga claves foráneas rotas ni anomalías estructurales."""
    with app.app_context():
        resultado = auditar_base_datos(db.session)
        assert resultado["correcta"] is True
        assert len(resultado["fks_invalidas"]) == 0
        assert len(resultado["sin_pk"]) == 0


def test_auditoria_pantallas_operativas_principales(client, app):
    """Verifica que todas las pantallas GET principales respondan con HTTP 200 sin errores de plantilla."""
    with app.app_context():
        # Obtener o crear datos de prueba válidos
        cat = Categoria.query.first()
        if not cat:
            cat = Categoria(nombre="Sub-12 Test", edad_min=20, edad_max=21)
            db.session.add(cat)
            db.session.flush()

        lugar = Lugar.query.first() or Lugar(nombre="Cancha Central")
        db.session.add(lugar)
        db.session.flush()

        alumno = Alumno.query.first()
        if not alumno:
            alumno = Alumno(
                nombre="Lucas", apellido="Vargas", fecha_nacimiento=date(2014, 5, 10),
                ci="9876543", sexo="M", id_categoria=cat.id_categoria, estado="Activo"
            )
            db.session.add(alumno)
            db.session.flush()

        pago = Pago.query.first()
        if not pago:
            pago = Pago(
                id_alumno=alumno.id_alumno, mes_pagado="2026-03", fecha_pago=date(2026, 3, 5),
                fecha_vencimiento=date(2026, 4, 5), monto=Decimal("200.00"), modo_pago="Efectivo"
            )
            db.session.add(pago)
            db.session.flush()

        champ = Campeonato.query.first()
        if not champ:
            champ = Campeonato(nombre="Torneo Apertura 2026", fecha_inicio=date.today())
            db.session.add(champ)
            db.session.flush()

        db.session.commit()
        id_alumno = alumno.id_alumno
        id_pago = pago.id_pago
        id_champ = champ.id_campeonato

    rutas = [
        "/",
        "/alumnos/",
        "/alumnos/nuevo",
        f"/alumnos/{id_alumno}",
        f"/alumnos/{id_alumno}/editar",
        f"/alumnos/{id_alumno}/ficha.pdf",
        "/alumnos/asistencias",
        "/alumnos/exportar?columnas=nombre&columnas=apellido",
        "/alumnos/exportar.pdf?columnas=nombre&columnas=apellido",
        "/pagos/",
        f"/pagos/alumno/{id_alumno}/nuevo",
        f"/pagos/{id_pago}/comprobante",
        f"/pagos/{id_pago}/recibo.pdf",
        "/pagos/exportar-form",
        "/pagos/exportar?columnas=alumno&columnas=monto",
        "/pagos/exportar.pdf?columnas=alumno&columnas=monto",
        "/categorias/",
        "/categorias/nuevo",
        "/equipos/",
        "/equipos/nuevo",
        "/lugares/",
        "/lugares/nuevo",
        "/partidos/",
        "/partidos/nuevo",
        "/agenda/",
        "/agenda/nuevo",
        "/calendario/",
        "/calendario/entrenamientos",
        "/calendario/entrenamientos/nuevo",
        "/campeonatos/",
        "/campeonatos/nuevo",
        f"/campeonatos/{id_champ}",
        "/campeonatos/rivales",
        "/configuracion/",
        "/informacion/",
        "/informacion/auditoria",
        "/usuarios/",
        "/health",
        "/ping",
    ]

    for ruta in rutas:
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200, f"Error en ruta {ruta}: status {respuesta.status_code}"


def test_auditoria_flujo_cobro_directo_sin_caja(client, app):
    """Verifica que un pago se cree directamente sin necesidad de abrir caja, y genere su recibo PDF."""
    with app.app_context():
        cfg = Configuracion.obtener()
        cfg.monto_mensualidad = Decimal("220.00")
        db.session.commit()

        cat = Categoria.query.first()
        alumno = Alumno(
            nombre="Mateo", apellido="Roca", fecha_nacimiento=date(2016, 2, 1),
            ci="11223344", sexo="M", id_categoria=cat.id_categoria if cat else None, estado="Activo"
        )
        db.session.add(alumno)
        db.session.commit()
        id_alumno = alumno.id_alumno

    # 1. Registrar pago
    res_crear = client.post(
        f"/pagos/alumno/{id_alumno}/nuevo",
        data={
            "mes_pagado": "2026-05",
            "fecha_pago": "2026-05-02",
            "modo_pago": "Efectivo",
            "monto_abono": "220.00",
            "numero_operacion": "REC-001",
        },
        follow_redirects=True
    )
    assert res_crear.status_code == 200
    assert b"2026-05" in res_crear.data

    with app.app_context():
        pago_creado = Pago.query.filter_by(id_alumno=id_alumno, mes_pagado="2026-05").first()
        assert pago_creado is not None
        assert pago_creado.monto == Decimal("220.00")
        assert pago_creado.eliminado_en is None
        id_pago = pago_creado.id_pago

    # 2. Descargar recibo PDF
    res_pdf = client.get(f"/pagos/{id_pago}/recibo.pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.mimetype == "application/pdf"
    assert res_pdf.data.startswith(b"%PDF-")

    # 3. Anular pago con motivo obligatorio
    res_anular = client.post(
        f"/pagos/{id_pago}/eliminar",
        data={"motivo": "Error en monto digitado por tesorería"},
        follow_redirects=True
    )
    assert res_anular.status_code == 200

    with app.app_context():
        pago_anulado = db.session.get(Pago, id_pago)
        assert pago_anulado.eliminado_en is not None
        assert pago_anulado.anulacion is not None
        assert "Error en monto" in pago_anulado.anulacion.motivo


def test_auditoria_flujo_asistencia_por_defecto_presente(client, app):
    """Verifica que la asistencia se cargue por defecto con todos presentes y permita guardar y modificar estados."""
    with app.app_context():
        cat = Categoria.query.first()
        assert cat is not None, "Debe existir al menos una categoría en el sistema"

        a1 = Alumno(nombre="Gael", apellido="Pinto", fecha_nacimiento=date(2018, 4, 1), ci="990011", sexo="M", id_categoria=cat.id_categoria, estado="Activo")
        a2 = Alumno(nombre="Esteban", apellido="Soliz", fecha_nacimiento=date(2018, 6, 12), ci="990022", sexo="M", id_categoria=cat.id_categoria, estado="Activo")
        db.session.add_all([a1, a2])
        db.session.commit()
        id_cat = cat.id_categoria
        id_a1, id_a2 = a1.id_alumno, a2.id_alumno

    # 1. Cargar formulario de toma de asistencia
    res_form = client.get(f"/alumnos/asistencias?tab=tomar&id_categoria={id_cat}&fecha=2026-06-15")
    assert res_form.status_code == 200
    assert b"Gael" in res_form.data
    assert b"Esteban" in res_form.data
    # Verificar que el selector tiene 'checked' por defecto en Presente
    assert b'checked' in res_form.data

    # 2. Guardar asistencia: a1 Presente, a2 Ausente con justificación
    res_guardar = client.post(
        "/alumnos/asistencias/guardar",
        data={
            "id_categoria": str(id_cat),
            "fecha": "2026-06-15",
            "hora": "16:00",
            "lugar": "Cancha 2",
            f"estado_{id_a1}": "Presente",
            f"justificacion_{id_a1}": "",
            f"estado_{id_a2}": "Ausente",
            f"justificacion_{id_a2}": "Permiso por examen escolar",
        },
        follow_redirects=True
    )
    assert res_guardar.status_code == 200

    # 3. Comprobar registros en base de datos
    with app.app_context():
        asist_a1 = AsistenciaEntrenamiento.query.filter_by(id_alumno=id_a1).order_by(AsistenciaEntrenamiento.id_asistencia.desc()).first()
        asist_a2 = AsistenciaEntrenamiento.query.filter_by(id_alumno=id_a2).order_by(AsistenciaEntrenamiento.id_asistencia.desc()).first()

        assert asist_a1 is not None and asist_a1.estado == "Presente"
        assert asist_a2 is not None and asist_a2.estado == "Ausente"
        assert asist_a2.justificacion == "Permiso por examen escolar"


def test_auditoria_roles_y_aislamiento_de_permisos(client, app):
    """Comprueba que Secretaría y Cobranzas tengan acceso sólo a lo que les corresponde y se aíslen de administración."""
    app.config["AUTH_REQUIRED"] = True
    try:
        with app.app_context():
            admin = Usuario.query.filter_by(nombre_usuario="admin").one()
            admin.debe_cambiar_clave = False
            db.session.commit()

        # Login admin
        client.post("/acceso/", data={"nombre_usuario": "admin", "contrasena": "00000"})

        with app.app_context():
            rol_cob = Rol.query.filter_by(nombre="Cobranzas").first()
            if not rol_cob:
                rol_cob = Rol(nombre="Cobranzas", descripcion="Cobranzas y recibos")
                db.session.add(rol_cob)
                db.session.commit()
            id_rol_cob = rol_cob.id_rol

        # Crear usuario Cobranzas
        client.post("/usuarios/nuevo", data={
            "nombre_usuario": "cajero_test", "nombre_completo": "Cajero Auditoria", "id_rol": id_rol_cob
        })

        # Salir de admin y entrar como Cobranzas
        client.post("/acceso/salir")
        client.post("/acceso/", data={"nombre_usuario": "cajero_test", "contrasena": "00000"})
        client.post("/configuracion/contrasena", data={
            "contrasena_actual": "00000", "contrasena_nueva": "55555", "confirmar_contrasena": "55555"
        })

        # Cobranzas puede ver pagos
        assert client.get("/pagos/").status_code == 200

        # Cobranzas NO puede administrar usuarios ni auditoría interna
        assert client.get("/usuarios/").status_code == 403
        assert client.get("/informacion/auditoria").status_code == 403
        assert client.get("/informacion/").status_code == 403

    finally:
        app.config["AUTH_REQUIRED"] = False
