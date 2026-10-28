def test_pantallas_principales(client):
    rutas = [
        "/", "/informacion/", "/alumnos/", "/pagos/", "/categorias/", "/equipos/",
        "/partidos/", "/agenda/", "/calendario/",
        "/calendario/entrenamientos", "/campeonatos/",
        "/campeonatos/rivales", "/lugares/", "/lugares/nuevo",
        "/configuracion/",
        "/gestion/contabilidad", "/gestion/inventario", "/gestion/ventas",
        "/gestion/proveedores", "/informacion/auditoria",
        "/gestion/pagos-programados", "/gestion/pagos-programados/nuevo",
    ]
    for ruta in rutas:
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200, ruta


def test_csrf_activo_fuera_de_pruebas(app):
    assert "csrf" in app.extensions


def test_encabezados_de_seguridad(client):
    respuesta = client.get("/")
    assert respuesta.headers["X-Frame-Options"] == "DENY"
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert "camera=()" in respuesta.headers["Permissions-Policy"]


def test_endpoints_monitoreo_ping_health_resilientes(client):
    # Validar que /ping y /health respondan 200 sin exigir autenticación
    # tanto con barra final como sin ella, y con múltiples verbos HTTP.
    for ruta in ["/ping", "/ping/"]:
        assert client.get(ruta).status_code == 200
        assert client.head(ruta).status_code == 200
        assert client.post(ruta).status_code == 200
        assert client.options(ruta).status_code == 200

    for ruta in ["/health", "/health/"]:
        assert client.get(ruta).status_code == 200
        assert client.head(ruta).status_code == 200
        assert client.options(ruta).status_code == 200

