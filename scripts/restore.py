import argparse
import os
import shutil
import sqlite3
import socket
from pathlib import Path

from app import create_app
from app.extensions import db
from app.utils.backup import crear_respaldo, ruta_sqlite


parser = argparse.ArgumentParser(description="Restaura un respaldo SQLite validado.")
parser.add_argument("respaldo", type=Path)
parser.add_argument("--confirmar", action="store_true")
args = parser.parse_args()
if not args.confirmar:
    raise SystemExit("Use --confirmar para ejecutar la restauración.")
if not args.respaldo.exists():
    raise SystemExit("El archivo de respaldo no existe.")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as comprobador:
    comprobador.settimeout(0.4)
    if comprobador.connect_ex(("127.0.0.1", 5000)) == 0:
        raise SystemExit(
            "El sistema está abierto en el puerto 5000. Ciérrelo antes de restaurar."
        )

conexion = sqlite3.connect(str(args.respaldo))
resultado = conexion.execute("PRAGMA integrity_check").fetchone()[0]
tablas = {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}
conexion.close()
if resultado != "ok":
    raise SystemExit(f"El respaldo no es válido: {resultado}")
if not {"alumno", "pago", "configuracion"}.issubset(tablas):
    raise SystemExit("El archivo no corresponde a una base válida del sistema.")

app = create_app()
destino = ruta_sqlite(app)
with app.app_context():
    seguridad = crear_respaldo(app, "antes_restaurar")
    db.session.remove()
    db.engine.dispose()
temporal = destino.with_suffix(".restaurando.tmp")
shutil.copy2(args.respaldo, temporal)
conexion = sqlite3.connect(str(temporal))
validacion = conexion.execute("PRAGMA integrity_check").fetchone()[0]
conexion.close()
if validacion != "ok":
    temporal.unlink(missing_ok=True)
    raise SystemExit(f"La copia temporal no superó la validación: {validacion}")
os.replace(temporal, destino)
for sufijo in ("-wal", "-shm"):
    Path(str(destino) + sufijo).unlink(missing_ok=True)
print(f"Base restaurada. Copia previa: {seguridad}")
