"""Pruebas de compatibilidad con PostgreSQL, normalización de URLs y herramientas de migración."""

import pytest
from pathlib import Path
from config import _obtener_database_uri, _obtener_engine_options
from scripts.migrar_a_postgresql import normalizar_postgres_url, migrar_datos
from scripts.exportar_para_postgresql import exportar_sql, escapar_valor_pg


def test_normalizar_postgres_url_convierte_prefijo(monkeypatch):
    url_legacy = "postgres://usuario:clave@db.render.com:5432/academia"
    esperado = "postgresql://usuario:clave@db.render.com:5432/academia"
    assert normalizar_postgres_url(url_legacy) == esperado

    url_estandar = "postgresql://usuario:clave@localhost:5432/academia"
    assert normalizar_postgres_url(url_estandar) == url_estandar


def test_obtener_database_uri_con_variable(monkeypatch):
    monkeypatch.delenv("USE_LOCAL_SQLITE", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgres://test_user:pass@host/bd")
    uri = _obtener_database_uri()
    assert uri.startswith("postgresql") and "test_user:pass@host/bd" in uri

    for var in ["DATABASE_URL", "NAME_OF_VARIABLE", "DIRECT_URL", "SUPABASE_DATABASE_URL", "POSTGRES_URL"]:
        monkeypatch.delenv(var, raising=False)
    uri_sqlite = _obtener_database_uri()
    assert uri_sqlite.startswith("sqlite:///")


def test_obtener_engine_options_por_dialecto():
    opciones_sqlite = _obtener_engine_options("sqlite:///instance/academia.db")
    assert opciones_sqlite["pool_pre_ping"] is True
    assert opciones_sqlite["connect_args"]["timeout"] == 5

    opciones_pg = _obtener_engine_options("postgresql://user:pass@localhost:5432/db")
    assert opciones_pg["pool_pre_ping"] is True
    assert "timeout" not in opciones_pg["connect_args"]
    assert opciones_pg["connect_args"]["connect_timeout"] == 10
    assert opciones_pg["pool_size"] == 10
    assert opciones_pg["max_overflow"] == 20
    assert opciones_pg["pool_recycle"] == 300


def test_escapar_valor_pg():
    assert escapar_valor_pg(None) == "NULL"
    assert escapar_valor_pg(1, es_booleano=True) == "TRUE"
    assert escapar_valor_pg(0, es_booleano=True) == "FALSE"
    assert escapar_valor_pg("O'Connor") == "'O''Connor'"
    assert escapar_valor_pg(125.50) == "125.5"


def test_migracion_dry_run_ejecuta_sin_error(tmp_path):
    archivo_db = Path("instance/academia.db")
    if archivo_db.exists():
        migrar_datos(archivo_db, "", dry_run=True)


def test_exportar_sql_genera_archivo_valido(tmp_path):
    archivo_db = Path("instance/academia.db")
    salida = tmp_path / "test_dump.sql"
    if archivo_db.exists():
        exportar_sql(archivo_db, salida)
        assert salida.exists()
        contenido = salida.read_text(encoding="utf-8")
        assert "BEGIN;" in contenido
        assert "COMMIT;" in contenido
        assert "SET CONSTRAINTS ALL DEFERRED;" in contenido
