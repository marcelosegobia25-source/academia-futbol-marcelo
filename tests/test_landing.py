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
    assert "lp-floating-wa" in contenido
    assert "badge-morning-solid" in contenido
    assert "badge-afternoon-solid" in contenido
    assert "badge-weekend-solid" in contenido
    assert "lp-hero-bg-media" in contenido
    assert "lp-cat-card" in contenido
    assert "lp-schedule-card" in contenido
    assert "lp-cat-top-bar" in contenido
    assert "bg-success-subtle" not in contenido


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


def test_landing_imagenes_de_fondo_css(client):
    respuesta = client.get("/static/css/landing.css")
    assert respuesta.status_code == 200
    contenido = respuesta.data.decode("utf-8")
    assert "hero_stadium.jpg" in contenido
    assert "tiro_potencia.jpg" in contenido
    assert "gol_red.jpg" in contenido

