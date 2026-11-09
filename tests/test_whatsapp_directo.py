from datetime import date
from app.extensions import db
from app.models import Alumno, Categoria, Pago
from app.utils.whatsapp import (
    formatear_numero_whatsapp,
    obtener_plantillas_whatsapp,
    guardar_plantillas_whatsapp,
    PLANTILLAS_PREDETERMINADAS,
)


def test_formatear_numero_whatsapp():
    # Número local boliviano de 8 dígitos
    assert formatear_numero_whatsapp("71234567", "591") == "59171234567"
    assert formatear_numero_whatsapp("60987654", "591") == "59160987654"
    # Número con espacios, guiones o signos
    assert formatear_numero_whatsapp("+591 712-34567", "591") == "59171234567"
    # Número ya con código de país
    assert formatear_numero_whatsapp("59171234567", "591") == "59171234567"
    # Número internacional de otro país
    assert formatear_numero_whatsapp("5491122334455", "591") == "5491122334455"
    # Vacío o nulo
    assert formatear_numero_whatsapp("", "591") == ""
    assert formatear_numero_whatsapp(None, "591") == ""


def test_plantillas_whatsapp_claves():
    plantillas = obtener_plantillas_whatsapp()
    claves_esperadas = ["prefijo_pais", "deuda", "proximo_vencer", "al_dia", "citacion", "comunicado", "cumpleanos", "personalizado", "recibo_pago"]
    for clave in claves_esperadas:
        assert clave in plantillas
        assert len(plantillas[clave]) > 0


def test_configuracion_whatsapp_get_y_post(client, app):
    # GET a la vista de configuración de WhatsApp
    resp_get = client.get("/configuracion/whatsapp")
    assert resp_get.status_code == 200
    assert b"Plantillas de WhatsApp" in resp_get.data
    assert b"Variables din\xc3\xa1micas disponibles" in resp_get.data
    assert b"name=\"deuda\"" in resp_get.data
    assert b"name=\"prefijo_pais\"" in resp_get.data

    # POST para actualizar plantilla de deuda
    resp_post = client.post("/configuracion/whatsapp", data={
        "accion": "guardar",
        "prefijo_pais": "591",
        "deuda": "Mensaje personalizado de prueba para regularizar cuota.",
        "proximo_vencer": "Aviso proximo vencer prueba",
        "al_dia": "Al dia prueba",
        "citacion": "Citacion prueba",
        "comunicado": "Comunicado prueba",
        "cumpleanos": "Cumpleanos prueba",
        "personalizado": "Personalizado prueba"
    }, follow_redirects=True)
    assert resp_post.status_code == 200
    assert b"Plantillas de mensajes de WhatsApp guardadas correctamente" in resp_post.data

    with app.app_context():
        actualizadas = obtener_plantillas_whatsapp()
        assert actualizadas["deuda"] == "Mensaje personalizado de prueba para regularizar cuota."

    # POST para restablecer
    resp_rest = client.post("/configuracion/whatsapp", data={"accion": "restablecer"}, follow_redirects=True)
    assert resp_rest.status_code == 200
    assert b"Se han restablecido las plantillas predeterminadas" in resp_rest.data


def test_modal_whatsapp_presente_en_base(client):
    resp = client.get("/panel")
    assert resp.status_code == 200
    assert b"modalWhatsAppDirecto" in resp.data
    assert b"abrirModalWhatsAppAlumno" in resp.data
    assert b"waAbrirWhatsAppChat" in resp.data


def test_botones_whatsapp_en_listado_y_detalle(client, app):
    with app.app_context():
        categoria = Categoria.query.first()
        alumno = Alumno(
            nombre="Mateo",
            apellido="Rios",
            fecha_nacimiento=date(2014, 5, 10),
            ci="88990011",
            telefono="77665544",
            tutor="Carlos Rios",
            categoria=categoria,
            estado="Activo",
        )
        db.session.add(alumno)
        db.session.commit()
        id_alumno = alumno.id_alumno

        # Crear un pago para probar también en tabla de pagos
        pago = Pago(
            id_alumno=id_alumno,
            mes_pagado="2026-11",
            fecha_pago=date(2026, 11, 1),
            fecha_vencimiento=date(2026, 12, 1),
            monto=150.0,
            modo_pago="Efectivo",
        )
        db.session.add(pago)
        db.session.commit()

    # 1. En listado de alumnos
    resp_alumnos = client.get("/alumnos/")
    assert resp_alumnos.status_code == 200
    assert b"Mateo" in resp_alumnos.data
    assert b"abrirModalWhatsAppAlumno" in resp_alumnos.data
    assert b"77665544" in resp_alumnos.data

    # 2. En detalle de alumno
    resp_detalle = client.get(f"/alumnos/{id_alumno}")
    assert resp_detalle.status_code == 200
    assert b"Mensaje WhatsApp" in resp_detalle.data
    assert b"Notificar estado por WhatsApp" in resp_detalle.data

    # 3. En listado de pagos
    resp_pagos = client.get("/pagos/")
    assert resp_pagos.status_code == 200
    assert b"abrirModalWhatsAppAlumno" in resp_pagos.data
    assert b"Mateo Rios" in resp_pagos.data


def test_difusion_masiva_whatsapp_presente_en_vistas(client, app):
    with app.app_context():
        categoria = Categoria.query.first()
        alumno = Alumno(
            nombre="Lucas",
            apellido="Suarez",
            fecha_nacimiento=date(2013, 3, 15),
            ci="99887766",
            telefono="78901234",
            tutor="Maria Suarez",
            categoria=categoria,
            estado="Activo",
        )
        db.session.add(alumno)
        db.session.commit()

    # Base contiene el modal de difusión masiva (probado en panel que hereda de base.html)
    resp_base = client.get("/panel")
    assert resp_base.status_code == 200
    assert b"modalDifusionWhatsApp" in resp_base.data
    assert b"abrirDifusionWhatsAppAlumnos" in resp_base.data
    assert b"difusionEnviarSiguiente" in resp_base.data

    # Alumnos contiene el botón de mensaje masivo y datos JSON en las filas
    resp_alumnos = client.get("/alumnos/")
    assert resp_alumnos.status_code == 200
    assert b"abrirDifusionWhatsAppAlumnos()" in resp_alumnos.data
    assert b"data-alumno-json" in resp_alumnos.data
    assert b"Lucas" in resp_alumnos.data

    # Pagos contiene el botón de mensaje masivo
    resp_pagos = client.get("/pagos/")
    assert resp_pagos.status_code == 200
    assert b"abrirDifusionWhatsAppPagos()" in resp_pagos.data


def test_comprobante_pago_whatsapp_y_compartir(client, app):
    with app.app_context():
        categoria = Categoria.query.first()
        alumno = Alumno(
            nombre="Valeria",
            apellido="Mendoza",
            fecha_nacimiento=date(2015, 8, 20),
            ci="77112233",
            telefono="71234567",
            tutor="Gabriel Mendoza",
            categoria=categoria,
            estado="Activo",
        )
        db.session.add(alumno)
        db.session.commit()

        pago = Pago(
            id_alumno=alumno.id_alumno,
            mes_pagado="2026-11",
            fecha_pago=date(2026, 11, 6),
            fecha_vencimiento=date(2026, 12, 6),
            monto=200.0,
            modo_pago="Efectivo",
        )
        db.session.add(pago)
        db.session.commit()
        id_pago = pago.id_pago

    # Acceder a la vista del comprobante
    resp = client.get(f"/pagos/{id_pago}/comprobante")
    assert resp.status_code == 200
    # Verificar que están presentes las opciones de compartir y WhatsApp directo
    assert b"Pago registrado con" in resp.data
    assert b"enviarWhatsAppDirecto" in resp.data
    assert b"compartirComprobante" in resp.data
    assert b"btn-compartir" in resp.data
    assert b"71234567" in resp.data
    assert b"Enviar a WhatsApp (71234567)" in resp.data
    assert b"recibo_pago" in resp.data

