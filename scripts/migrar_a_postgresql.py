#!/usr/bin/env python3
"""Script de migración integral de datos desde SQLite local a PostgreSQL (Nube o Local).

Uso:
    python scripts/migrar_a_postgresql.py --postgres "postgresql://usuario:clave@host:5432/nombre_bd"
    O configurando la variable de entorno:
    DATABASE_URL="postgresql://usuario:clave@host:5432/nombre_bd" python scripts/migrar_a_postgresql.py
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Configurar encoding UTF-8 en consola de Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, inspect, text, Boolean, Integer, Numeric
from app import create_app
from app.extensions import db


def normalizar_postgres_url(url: str) -> str:
    """Asegura que el protocolo sea postgresql+psycopg2:// requerido por SQLAlchemy."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def migrar_datos(sqlite_path: Path, postgres_url: str, limpiar: bool = False, dry_run: bool = False):
    print("=" * 80)
    print("MIGRACIÓN DE BASE DE DATOS: SQLite ➔ PostgreSQL")
    print("=" * 80)

    if not sqlite_path.exists():
        print(f"❌ Error: No se encontró el archivo SQLite de origen en: {sqlite_path}")
        sys.exit(1)

    print(f"📁 Origen SQLite:       {sqlite_path} ({sqlite_path.stat().st_size / (1024*1024):.2f} MB)")
    
    # Ocultar contraseña en el print del destino
    url_segura = postgres_url
    if "@" in url_segura and ":" in url_segura:
        partes = url_segura.split("@")
        credenciales = partes[0].split(":")
        if len(credenciales) >= 3:
            url_segura = f"{credenciales[0]}:{credenciales[1]}:****@{partes[1]}"
    print(f"🌐 Destino PostgreSQL:   {url_segura}")
    print("=" * 80)

    # Inicializar app Flask para tener acceso a los metadatos de modelos
    app = create_app()

    # Motores SQLAlchemy
    engine_sqlite = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    inspector_sqlite = inspect(engine_sqlite)
    tablas_sqlite = set(inspector_sqlite.get_table_names())

    if dry_run:
        print("🔍 MODO DRY-RUN: Verificando datos en SQLite...\n")
        total_filas = 0
        for tabla in sorted(tablas_sqlite):
            with engine_sqlite.connect() as conn:
                cant = conn.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).fetchone()[0]
                total_filas += cant
                if cant > 0:
                    print(f"  • {tabla:<35} {cant:>5} filas")
        print("\n" + "-" * 50)
        print(f"Total tablas detectadas: {len(tablas_sqlite)}")
        print(f"Total registros a migrar: {total_filas}")
        print("-" * 50)
        print("\n✅ Verificación SQLite exitosa. Listo para migrar cuando indiques la URL de PostgreSQL.")
        return

    engine_pg = create_engine(
        postgres_url,
        pool_pre_ping=True,
        pool_recycle=60,
        connect_args={"connect_timeout": 30, "keepalives": 1, "keepalives_idle": 15},
    )

    # Probar conexión PostgreSQL
    try:
        with engine_pg.connect() as conn:
            version_pg = conn.execute(text("SELECT version()")).fetchone()[0]
            print(f"✅ Conexión a PostgreSQL exitosa:")
            print(f"   {version_pg[:70]}...\n")
    except Exception as e:
        print(f"❌ No se pudo conectar a PostgreSQL: {e}")
        print("\nVerifica que la URL sea correcta, el servidor esté en ejecución y acepte conexiones.")
        sys.exit(1)

    with app.app_context():
        # Crear todas las tablas en PostgreSQL con SQLAlchemy según los modelos actuales
        print("🔨 Preparando esquema en PostgreSQL...")
        if limpiar:
            print("⚠️ Opción --limpiar activada: vaciando tablas existentes en PostgreSQL...")
            try:
                with engine_pg.begin() as conn_trunc:
                    tablas_existentes = inspect(engine_pg).get_table_names()
                    if tablas_existentes:
                        tablas_quoted = ", ".join([f'"{t}"' for t in tablas_existentes if not t.startswith("pg_")])
                        conn_trunc.execute(text(f"TRUNCATE TABLE {tablas_quoted} RESTART IDENTITY CASCADE;"))
                        print("✅ Tablas vaciadas con éxito mediante TRUNCATE CASCADE.")
            except Exception as e_trunc:
                print(f"ℹ️ Fallback a drop_all ({e_trunc})...")
                db.metadata.drop_all(bind=engine_pg)

        db.metadata.create_all(bind=engine_pg)
        print("✅ Todas las tablas (57 modelos) creadas/verificadas en PostgreSQL con sus índices y claves foráneas.\n")

    # Ordenar tablas respetando dependencias foráneas
    tablas_ordenadas = db.metadata.sorted_tables
    tablas_modelo_map = {t.name: t for t in tablas_ordenadas}

    # Agregar tablas que pudieran no estar en sorted_tables (ej. schema_migration)
    lista_tablas = [t.name for t in tablas_ordenadas]
    for t_sqlite in sorted(tablas_sqlite):
        if t_sqlite not in lista_tablas and not t_sqlite.startswith("sqlite_"):
            lista_tablas.append(t_sqlite)

    resumen = []
    print("📦 Migrando datos tabla por tabla...\n")

    for nombre_tabla in lista_tablas:
        if nombre_tabla not in tablas_sqlite:
            continue

        with engine_sqlite.connect() as conn_sq:
            filas_sqlite = conn_sq.execute(text(f'SELECT * FROM "{nombre_tabla}"')).fetchall()
            if not filas_sqlite:
                continue

            columnas = list(conn_sq.execute(text(f'SELECT * FROM "{nombre_tabla}" LIMIT 0')).keys())

        # Detectar tipos de columnas para transformar booleanos SQLite (0/1 -> False/True)
        cols_booleanas = set()
        tabla_obj = tablas_modelo_map.get(nombre_tabla)
        if tabla_obj is not None:
            for col in tabla_obj.columns:
                if isinstance(col.type, Boolean):
                    cols_booleanas.add(col.name)

        # Preparar registros transformados
        registros = []
        for fila in filas_sqlite:
            item = dict(zip(columnas, fila))
            # Limpiar literales 'None' o 'null'
            for k, v in list(item.items()):
                if isinstance(v, str) and v in ("None", "null"):
                    item[k] = None
            # Ajustar tipos booleanos
            for col_bool in cols_booleanas:
                if col_bool in item and item[col_bool] is not None:
                    item[col_bool] = bool(item[col_bool])
            registros.append(item)

        # Inserción y commit por tabla individual para evitar timeouts en el pooler de Supabase
        chunk_size = 200
        for intento in range(3):
            try:
                with engine_pg.begin() as conn_pg:
                    for i in range(0, len(registros), chunk_size):
                        chunk = registros[i:i + chunk_size]
                        cols_sql = ", ".join([f'"{c}"' for c in columnas])
                        vals_sql = ", ".join([f":{c}" for c in columnas])
                        insert_stmt = text(f'INSERT INTO "{nombre_tabla}" ({cols_sql}) VALUES ({vals_sql})')
                        conn_pg.execute(insert_stmt, chunk)
                break
            except Exception as e_insert:
                if intento == 2:
                    raise
                print(f"  ⚠️ Reintentando {nombre_tabla} por reconexión ({e_insert})...")

        print(f"  ✓ {nombre_tabla:<32} {len(registros):>5} filas migradas")
        resumen.append((nombre_tabla, len(registros)))

    # Actualizar secuencias automáticas (SERIAL / IDENTITY) en PostgreSQL
    print("\n🔢 Sincronizando secuencias de Primary Keys en PostgreSQL...")
    with engine_pg.begin() as conn_sync:
        for nombre_tabla in lista_tablas:
            tabla_obj = tablas_modelo_map.get(nombre_tabla)
            if tabla_obj is not None:
                pks = [c for c in tabla_obj.primary_key.columns if isinstance(c.type, Integer)]
                for pk in pks:
                    sql_seq = text(f"""
                        SELECT pg_get_serial_sequence('"{nombre_tabla}"', '{pk.name}')
                    """)
                    seq_res = conn_sync.execute(sql_seq).scalar()
                    if seq_res:
                        sql_setval = text(f"""
                            SELECT setval('{seq_res}', COALESCE(MAX("{pk.name}"), 1), MAX("{pk.name}") IS NOT NULL)
                            FROM "{nombre_tabla}"
                        """)
                        conn_sync.execute(sql_setval)

        # Asegurar registro de migraciones 1..32 en schema_migration
        from app.migrations import MIGRACIONES
        conn_sync.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migration (
                version INTEGER PRIMARY KEY,
                nombre VARCHAR(160) NOT NULL,
                aplicada_en TIMESTAMP NOT NULL
            )
        """))
        for version, nombre, _ in MIGRACIONES:
            conn_sync.execute(text("""
                INSERT INTO schema_migration (version, nombre, aplicada_en)
                VALUES (:version, :nombre, :fecha)
                ON CONFLICT (version) DO NOTHING
            """), {
                "version": version,
                "nombre": nombre,
                "fecha": datetime.now(timezone.utc).replace(tzinfo=None),
            })

    print("\n" + "=" * 80)
    print("RESUMEN DE AUDITORÍA Y VERIFICACIÓN")
    print("=" * 80)
    print(f"{'TABLA':<35} | {'ORIGEN (SQLite)':<16} | {'DESTINO (PG)':<16} | ESTADO")
    print("-" * 80)

    total_sq = 0
    total_pg = 0
    errores = 0

    with engine_sqlite.connect() as c_sq, engine_pg.connect() as c_pg:
        for tabla, _ in resumen:
            cnt_sq = c_sq.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).fetchone()[0]
            cnt_pg = c_pg.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).fetchone()[0]
            total_sq += cnt_sq
            total_pg += cnt_pg
            coincide = cnt_sq == cnt_pg
            if not coincide:
                errores += 1
            print(f"{tabla:<35} | {cnt_sq:<16} | {cnt_pg:<16} | {'✅ OK' if coincide else '❌ DIFERENCIA'}")

    print("-" * 80)
    print(f"{'TOTALES':<35} | {total_sq:<16} | {total_pg:<16} | {'✅ 100% COINCIDENCIA' if errores == 0 else f'❌ {errores} DISCREPANCIAS'}")
    print("=" * 80)

    if errores == 0:
        print("\n🎉 ¡MIGRACIÓN COMPLETADA CON ÉXITO ABSOLUTO!")
        print("La base de datos PostgreSQL está completamente sincronizada y lista para producción en la nube.")
    else:
        print(f"\n⚠️ La migración finalizó con {errores} discrepancias. Revisa los mensajes anteriores.")


def main():
    parser = argparse.ArgumentParser(description="Migrador de Academia de Fútbol: SQLite ➔ PostgreSQL")
    parser.add_argument(
        "--sqlite",
        type=Path,
        default=ROOT / "instance" / "academia.db",
        help="Ruta al archivo academia.db de SQLite (por defecto: instance/academia.db)",
    )
    parser.add_argument(
        "--postgres",
        type=str,
        default=os.environ.get("DATABASE_URL"),
        help="URL de conexión PostgreSQL (ej. postgresql://user:pass@host:5432/dbname). Si no se indica, lee DATABASE_URL.",
    )
    parser.add_argument(
        "--limpiar",
        action="store_true",
        help="Elimina las tablas existentes en PostgreSQL antes de migrar.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verifica los datos en SQLite sin escribir en PostgreSQL.",
    )
    args = parser.parse_args()

    if not args.postgres and not args.dry_run:
        print("❌ Debes indicar la URL de PostgreSQL mediante el parámetro --postgres o la variable DATABASE_URL.")
        print("\nEjemplo:")
        print('  python scripts/migrar_a_postgresql.py --postgres "postgresql://postgres:postgres@localhost:5432/academia"')
        sys.exit(1)

    pg_url = normalizar_postgres_url(args.postgres) if args.postgres else ""
    migrar_datos(args.sqlite, pg_url, limpiar=args.limpiar, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
