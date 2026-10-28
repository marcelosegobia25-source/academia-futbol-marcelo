import sqlite3

from app.utils.integridad import auditar_sqlite


def test_auditoria_detecta_tabla_sin_pk_y_foranea_invalida(tmp_path):
    ruta = tmp_path / "auditoria.db"
    conexion = sqlite3.connect(ruta)
    conexion.executescript("""
        PRAGMA foreign_keys=OFF;
        CREATE TABLE padre (id INTEGER PRIMARY KEY);
        CREATE TABLE hijo (id INTEGER PRIMARY KEY, id_padre INTEGER REFERENCES padre(id));
        CREATE TABLE legado (dato TEXT);
        INSERT INTO hijo(id,id_padre) VALUES (1,999);
    """)
    conexion.commit()
    conexion.close()
    resultado = auditar_sqlite(ruta)
    assert resultado["integridad"] == "ok"
    assert resultado["sin_pk"] == ["legado"]
    assert len(resultado["fks_invalidas"]) == 1
    assert not resultado["correcta"]


def test_panel_de_auditoria_responde(client):
    assert client.get("/informacion/auditoria").status_code == 200


def test_auditar_base_datos_session(app):
    from app.utils.integridad import auditar_base_datos
    from app.extensions import db
    with app.app_context():
        res = auditar_base_datos(db.session, "TestDB")
        assert res["existe"] is True
        assert res["correcta"] is True
        assert len(res["alertas"]) == 0


def test_auditoria_registra_ip_cliente(app):
    from app.extensions import db
    from app.models import Auditoria
    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "192.168.1.55"}):
        a1 = Auditoria(modulo="Test", accion="Prueba IP Remote", detalle="Detalle IP")
        db.session.add(a1)
        db.session.commit()
        assert a1.ip == "192.168.1.55"

    with app.test_request_context("/", headers={"X-Forwarded-For": "203.0.113.195, 10.0.0.1"}):
        a2 = Auditoria(modulo="Test", accion="Prueba IP Proxy", detalle="Detalle Proxy")
        db.session.add(a2)
        db.session.commit()
        assert a2.ip == "203.0.113.195"

    with app.test_request_context("/", headers={"CF-Connecting-IP": "198.51.100.42"}):
        a3 = Auditoria(modulo="Test", accion="Prueba IP Cloudflare", detalle="Detalle Cloudflare")
        db.session.add(a3)
        db.session.commit()
        assert a3.ip == "198.51.100.42"


def test_auditoria_template_contiene_columna_ip(client):
    respuesta = client.get("/informacion/auditoria")
    assert respuesta.status_code == 200
    assert "<th>IP</th>".encode("utf-8") in respuesta.data

