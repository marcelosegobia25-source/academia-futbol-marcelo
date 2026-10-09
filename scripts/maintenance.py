"""Mantenimiento seguro de SQLite para una instalación local."""
import argparse
import sqlite3
from datetime import datetime

from app import create_app
from app.utils.backup import crear_respaldo, ruta_sqlite


parser = argparse.ArgumentParser()
parser.add_argument("--vacuum", action="store_true", help="Compacta la base; requiere espacio libre.")
args = parser.parse_args()

app = create_app()
with app.app_context():
    respaldo = crear_respaldo(app, "antes_mantenimiento")
    ruta = ruta_sqlite(app)

conexion = sqlite3.connect(str(ruta), timeout=30)
try:
    integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
    if integridad != "ok":
        raise SystemExit(f"Integridad inválida: {integridad}")
    conexion.execute("PRAGMA optimize")
    conexion.execute("ANALYZE")
    if args.vacuum:
        conexion.execute("VACUUM")
    conexion.commit()
    wal = conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
finally:
    conexion.close()

print(f"Mantenimiento completado {datetime.now():%d/%m/%Y %H:%M}")
print(f"Respaldo previo: {respaldo}")
print(f"Checkpoint WAL: {wal}")
