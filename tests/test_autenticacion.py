from app.extensions import db
from app.models import Auditoria, Configuracion, Rol, Usuario


def activar_acceso(app):
    app.config["AUTH_REQUIRED"] = True
    with app.app_context():
        admin = Usuario.query.filter_by(nombre_usuario="admin").one()
        admin.debe_cambiar_clave = False
        db.session.commit()


def test_roles_restringen_finanzas_y_auditoria_identifica_actor(client, app):
    activar_acceso(app)
    assert client.post("/acceso/", data={"nombre_usuario": "admin", "contrasena": "00000"}).status_code == 302
    with app.app_context():
        rol = Rol.query.filter_by(nombre="Secretaría").one()
        id_rol = rol.id_rol
        id_admin = Usuario.query.filter_by(nombre_usuario="admin").one().id_usuario
    assert client.post("/usuarios/nuevo", data={
        "nombre_usuario": "secretaria", "nombre_completo": "Secretaría", "id_rol": id_rol,
    }).status_code == 302
    with app.app_context():
        auditoria = Auditoria.query.filter_by(modulo="Usuarios", accion="Crear").one()
        assert auditoria.id_usuario == id_admin
        assert auditoria.valor_nuevo
    client.post("/acceso/salir")
    assert client.post("/acceso/", data={"nombre_usuario": "secretaria", "contrasena": "00000"}).status_code == 302
    client.post("/configuracion/contrasena", data={
        "contrasena_actual": "00000", "contrasena_nueva": "12345", "confirmar_contrasena": "12345",
    })
    assert client.get("/alumnos/").status_code == 200
    assert client.get("/gestion/contabilidad").status_code == 403
    assert client.get("/informacion/").status_code == 403
    assert client.get("/usuarios/").status_code == 403


def test_administrador_no_puede_desactivar_su_propia_cuenta(client, app):
    activar_acceso(app)
    client.post("/acceso/", data={"nombre_usuario": "admin", "contrasena": "00000"})
    with app.app_context():
        admin = Usuario.query.filter_by(nombre_usuario="admin").one()
        id_admin, id_rol = admin.id_usuario, admin.id_rol
    client.post(f"/usuarios/{id_admin}/actualizar", data={"id_rol": id_rol, "activo": "0"})
    with app.app_context():
        assert db.session.get(Usuario, id_admin).activo


def test_administrador_puede_configurar_permisos_de_un_rol(client, app):
    activar_acceso(app)
    client.post("/acceso/", data={"nombre_usuario": "admin", "contrasena": "00000"})
    with app.app_context():
        rol = Rol.query.filter(Rol.nombre != "Administrador").order_by(Rol.id_rol).first()
        permiso = next(p for p in rol.permisos if p.codigo == "ver_alumnos")
        id_rol, id_permiso = rol.id_rol, permiso.id_permiso

    respuesta = client.post(
        f"/usuarios/roles/{id_rol}/permisos",
        data={"id_permiso": [str(id_permiso)]},
    )
    assert respuesta.status_code == 302
    with app.app_context():
        rol = db.session.get(Rol, id_rol)
        assert [p.codigo for p in rol.permisos] == ["ver_alumnos"]
        registro = Auditoria.query.filter_by(
                modulo="Usuarios", accion="Cambiar permisos"
        ).one()
        assert registro.valor_anterior and registro.valor_nuevo


def test_sistema_redirige_al_login_y_acepta_clave_inicial(client, app):
    activar_acceso(app)
    with app.app_context():
        admin = Usuario.query.filter_by(nombre_usuario="admin").one()
        admin.debe_cambiar_clave = True
        db.session.commit()

    restringida = client.get("/alumnos/")
    assert restringida.status_code == 302
    assert "/acceso/" in restringida.location

    formulario = client.get("/acceso/")
    assert formulario.status_code == 200
    assert b'exactamente 5 n' in formulario.data

    incorrecta = client.post("/acceso/", data={"contrasena": "12345"})
    assert incorrecta.status_code == 200
    assert b"Contrase" in incorrecta.data

    correcta = client.post(
        "/acceso/",
        data={"contrasena": "00000", "next": "/alumnos/"},
    )
    assert correcta.status_code == 302
    assert correcta.location.endswith("/configuracion/contrasena")
    obligada = client.get("/alumnos/")
    assert obligada.status_code == 302
    assert obligada.location.endswith("/configuracion/contrasena")
    assert client.post("/configuracion/contrasena", data={
        "contrasena_actual": "00000", "contrasena_nueva": "54321", "confirmar_contrasena": "54321",
    }).status_code == 302
    assert client.get("/alumnos/").status_code == 200


def test_login_rechaza_clave_que_no_tiene_cinco_digitos(client, app):
    activar_acceso(app)
    respuesta = client.post("/acceso/", data={"contrasena": "12a45"})
    assert respuesta.status_code == 200
    assert b"exactamente 5 n" in respuesta.data


def test_cambio_de_clave_exige_actual_y_actualiza_hash(client, app):
    activar_acceso(app)
    client.post("/acceso/", data={"contrasena": "00000"})

    incorrecta = client.post("/configuracion/contrasena", data={
        "contrasena_actual": "11111",
        "contrasena_nueva": "54321",
        "confirmar_contrasena": "54321",
    })
    assert incorrecta.status_code == 200

    correcta = client.post("/configuracion/contrasena", data={
        "contrasena_actual": "00000",
        "contrasena_nueva": "54321",
        "confirmar_contrasena": "54321",
    })
    assert correcta.status_code == 302
    with app.app_context():
        config = Configuracion.obtener()
        assert config.verificar_contrasena("54321")
        assert not config.verificar_contrasena("00000")
        assert config.contrasena_hash != "54321"

    client.post("/acceso/salir")
    assert client.post("/acceso/", data={"contrasena": "00000"}).status_code == 200
    assert client.post("/acceso/", data={"contrasena": "54321"}).status_code == 302


def test_login_no_permite_redireccion_externa(client, app):
    activar_acceso(app)
    respuesta = client.post(
        "/acceso/",
        data={"contrasena": "00000", "next": "https://ejemplo.test/robo"},
    )
    assert respuesta.status_code == 302
    assert respuesta.location.endswith("/informacion/")


def test_login_bloquea_intentos_repetidos(client, app):
    activar_acceso(app)
    for _ in range(5):
        client.post("/acceso/", data={"contrasena": "99999"})
    respuesta = client.post("/acceso/", data={"contrasena": "99999"})
    assert respuesta.status_code == 429
    assert b"bloqueado temporalmente" in respuesta.data
