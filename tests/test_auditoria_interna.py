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
