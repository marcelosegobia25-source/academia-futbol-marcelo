def test_landing_page_publica(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    contenido = respuesta.data.decode("utf-8")
    assert "Pasión, Disciplina" in contenido
    assert "Categorías Disponibles" in contenido
    assert "Horarios de Entrenamiento" in contenido
    assert "+100" in contenido
    assert "Alumnos Formados" in contenido
    assert "Metodología" in contenido
    assert "whatsapp" in contenido.lower()


def test_landing_page_ruta_alternativa(client):
    respuesta = client.get("/landing")
    assert respuesta.status_code == 200
    assert b"Inscripciones Abiertas" in respuesta.data


def test_panel_administrativo_disponible(client):
    respuesta = client.get("/panel")
    assert respuesta.status_code == 200
    assert b"Centro de Comando" in respuesta.data


def test_landing_es_publica_cuando_auth_requerido(app):
    # Probar que con autenticación activa, la landing no redirige al login
    app.config["AUTH_REQUIRED"] = True
    with app.test_client() as c:
        resp = c.get("/")
        assert resp.status_code == 200
        assert b"Categor\xc3\xadas Disponibles" in resp.data

        # Mientras que /panel sí exige autenticación y redirige a /acceso
        resp_panel = c.get("/panel")
        assert resp_panel.status_code == 302
        assert "/acceso" in resp_panel.headers["Location"]

