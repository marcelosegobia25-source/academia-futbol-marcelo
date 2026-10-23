#!/usr/bin/env python3
"""Exportador de datos desde SQLite hacia un script SQL nativo para PostgreSQL.

Genera un archivo .sql listo para ser ejecutado con psql o pegado directamente
en consolas de la nube (Supabase, Neon, Railway, Render, etc.).

Uso:
    python scripts/exportar_para_postgresql.py
    python scripts/exportar_para_postgresql.py --salida instance/respaldo_postgresql.sql
"""

import argparse
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# Configurar encoding UTF-8 en consola de Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, inspect, text, Boolean, Integer
from app import create_app
from app.extensions import db


def escapar_valor_pg(valor, es_booleano: bool = False) -> str:
    if valor is None:
        return "NULL"
    if es_booleano:
        return "TRUE" if bool(valor) else "FALSE"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, (int, float, Decimal)):
        return str(valor)
    if isinstance(valor, (datetime, date)):
        return f"'{valor.isoformat()}'"
    
    # Manejar strings y bytes
    texto = str(valor).replace("'", "''")
    return f"'{texto}'"


def exportar_sql(sqlite_path: Path, salida_path: Path):
    print("=" * 80)
    print("EXPORTADOR DE DATOS: SQLite ➔ Script SQL para PostgreSQL")
    print("=" * 80)

    if not sqlite_path.exists():
        print(f"❌ Error: No se encontró la base SQLite en: {sqlite_path}")
        sys.exit(1)

    print(f"📁 Origen:  {sqlite_path}")
    print(f"📄 Destino: {salida_path}")
    print("=" * 80)

    app = create_app()
    engine_sqlite = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    inspector_sqlite = inspect(engine_sqlite)
    tablas_sqlite = set(inspector_sqlite.get_table_names())

    with app.app_context():
        tablas_ordenadas = db.metadata.sorted_tables
        tablas_modelo_map = {t.name: t for t in tablas_ordenadas}

    lista_tablas = [t.name for t in tablas_ordenadas]
    for t in sorted(tablas_sqlite):
        if t not in lista_tablas and not t.startswith("sqlite_"):
            lista_tablas.append(t)

    lineas_sql = [
        "-- ============================================================================",
        f"-- Script completo DDL + DML para PostgreSQL - Generado: {datetime.now().isoformat()}",
        "-- Academia de Fútbol - Compatible con Supabase, Neon, Render y PostgreSQL 12+",
        "-- ============================================================================",
        "SET client_encoding = 'UTF8';",
        "SET standard_conforming_strings = on;",
        "SET check_function_bodies = false;",
        "SET client_min_messages = warning;",
        "",
        "BEGIN;",
        "",
        "-- ============================================================================",
        "-- 1. LIMPIEZA PREVIA (DROP TABLES EN ORDEN INVERSO DE DEPENDENCIAS)",
        "-- ============================================================================",
    ]

    for tabla in reversed(tablas_ordenadas):
        lineas_sql.append(f'DROP TABLE IF EXISTS "{tabla.name}" CASCADE;')
    lineas_sql.append('DROP TABLE IF EXISTS "schema_migration" CASCADE;')

    lineas_sql.append("")
    lineas_sql.append("-- ============================================================================")
    lineas_sql.append("-- 2. DEFINICIÓN DEL ESQUEMA (CREATE TABLES, ÍNDICES Y CONSTRAINTS)")
    lineas_sql.append("-- ============================================================================")
    lineas_sql.append("")

    with app.app_context():
        from sqlalchemy import create_mock_engine

        ddl_statements = []

        def dump_ddl(sql, *multiparams, **params):
            compiled = str(sql.compile(dialect=mock_engine.dialect)).strip()
            if compiled:
                ddl_statements.append(compiled + ";")

        mock_engine = create_mock_engine("postgresql://", dump_ddl)
        db.metadata.create_all(mock_engine)

        for stmt in ddl_statements:
            lineas_sql.append(stmt)
            lineas_sql.append("")

    # Tabla especial de control de migraciones
    lineas_sql.append("CREATE TABLE IF NOT EXISTS schema_migration (")
    lineas_sql.append("    version INTEGER PRIMARY KEY,")
    lineas_sql.append("    nombre VARCHAR(160) NOT NULL,")
    lineas_sql.append("    aplicada_en TIMESTAMP NOT NULL")
    lineas_sql.append(");")
    lineas_sql.append("")

    lineas_sql.append("-- ============================================================================")
    lineas_sql.append("-- 3. INSERCIÓN DE DATOS (DML)")
    lineas_sql.append("-- ============================================================================")
    lineas_sql.append("")

    total_tablas = 0
    total_filas = 0

    with engine_sqlite.connect() as conn:
        for nombre_tabla in lista_tablas:
            if nombre_tabla not in tablas_sqlite:
                continue

            filas = conn.execute(text(f'SELECT * FROM "{nombre_tabla}"')).fetchall()
            if not filas:
                continue

            total_tablas += 1
            total_filas += len(filas)
            print(f"  • Exportando {nombre_tabla:<32} ({len(filas)} filas)")

            columnas = list(conn.execute(text(f'SELECT * FROM "{nombre_tabla}" LIMIT 0')).keys())
            cols_booleanas = set()
            tabla_obj = tablas_modelo_map.get(nombre_tabla)
            if tabla_obj is not None:
                for col in tabla_obj.columns:
                    if isinstance(col.type, Boolean):
                        cols_booleanas.add(col.name)

            lineas_sql.append(f"-- Tabla: {nombre_tabla} ({len(filas)} filas)")
            cols_str = ", ".join([f'"{c}"' for c in columnas])

            for fila in filas:
                valores_escapados = []
                for col_name, val in zip(columnas, fila):
                    es_bool = col_name in cols_booleanas
                    valores_escapados.append(escapar_valor_pg(val, es_booleano=es_bool))
                vals_str = ", ".join(valores_escapados)
                lineas_sql.append(f'INSERT INTO "{nombre_tabla}" ({cols_str}) VALUES ({vals_str});')

            lineas_sql.append("")

        # Ajuste de secuencias (setval)
        lineas_sql.append("-- ============================================================================")
        lineas_sql.append("-- 4. AJUSTE DE SECUENCIAS SERIAL (Evita conflictos en futuros INSERTs)")
        lineas_sql.append("-- ============================================================================")
        for nombre_tabla in lista_tablas:
            tabla_obj = tablas_modelo_map.get(nombre_tabla)
            if tabla_obj is not None and len(tabla_obj.primary_key.columns) == 1:
                pk = list(tabla_obj.primary_key.columns)[0]
                if isinstance(pk.type, Integer) and not pk.foreign_keys:
                    lineas_sql.append(
                        f"SELECT CASE WHEN pg_get_serial_sequence('{nombre_tabla}', '{pk.name}') IS NOT NULL "
                        f"THEN setval(pg_get_serial_sequence('{nombre_tabla}', '{pk.name}'), "
                        f"COALESCE(MAX(\"{pk.name}\"), 1), MAX(\"{pk.name}\") IS NOT NULL) "
                        f"ELSE NULL END FROM \"{nombre_tabla}\";"
                    )

    lineas_sql.append("")
    lineas_sql.append("COMMIT;")
    lineas_sql.append("")

    salida_path.parent.mkdir(parents=True, exist_ok=True)
    with open(salida_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas_sql))

    tamano_kb = salida_path.stat().st_size / 1024
    print("\n" + "=" * 80)
    print(f"✅ ARCHIVO SQL GENERADO CON ÉXITO: {salida_path} ({tamano_kb:.1f} KB)")
    print(f"   Tablas exportadas: {total_tablas}")
    print(f"   Filas exportadas:  {total_filas}")
    print("=" * 80)
    print("\n💡 Puedes ejecutar este archivo en tu base de datos PostgreSQL remota:")
    print(f"   psql -h <host> -U <usuario> -d <base_datos> -f \"{salida_path}\"")
    print("   O copiar y pegar su contenido en el Editor SQL de Supabase / Neon / Render.")


def main():
    parser = argparse.ArgumentParser(description="Exporta datos de SQLite a script PostgreSQL .sql")
    parser.add_argument(
        "--sqlite",
        type=Path,
        default=ROOT / "instance" / "academia.db",
        help="Ruta al archivo academia.db",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "instance" / "academia_postgresql.sql",
        help="Ruta del archivo .sql a generar",
    )
    args = parser.parse_args()
    exportar_sql(args.sqlite, args.salida)


if __name__ == "__main__":
    main()
