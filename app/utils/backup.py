import os
import hashlib
import json
import sqlite3
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path


def ruta_sqlite(app):
    prefijo = "sqlite:///"
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith(prefijo):
        return None
    return Path(uri[len(prefijo):]).resolve()


def crear_respaldo(app, etiqueta="automatico"):
    origen = ruta_sqlite(app)
    if origen is None or not origen.exists():
        return None
    carpeta = origen.parent / "backups"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"academia_{etiqueta}_{datetime.now():%Y%m%d_%H%M%S}.db"
    conexion_origen = sqlite3.connect(str(origen), timeout=10)
    conexion_destino = sqlite3.connect(str(destino))
    try:
        conexion_origen.backup(conexion_destino)
        resultado = conexion_destino.execute("PRAGMA integrity_check").fetchone()[0]
        if resultado != "ok":
            raise RuntimeError(f"Respaldo inválido: {resultado}")
    finally:
        conexion_destino.close()
        conexion_origen.close()
    return destino


def crear_respaldo_diario(app):
    if not app.config.get("AUTO_BACKUP", True):
        return None
    origen = ruta_sqlite(app)
    if origen is None or not origen.exists():
        return None
    carpeta = origen.parent / "backups"
    patron = f"academia_automatico_{date.today():%Y%m%d}_*.db"
    if carpeta.exists() and next(carpeta.glob(patron), None):
        return None
    destino = crear_respaldo(app)
    limite = datetime.now() - timedelta(days=app.config.get("BACKUP_RETENTION_DAYS", 30))
    for archivo in carpeta.glob("academia_automatico_*.db"):
        if datetime.fromtimestamp(archivo.stat().st_mtime) < limite:
            archivo.unlink()
    return destino


def crear_respaldo_completo(app):
    """Empaqueta una copia consistente de SQLite, fotos y hashes SHA-256."""
    base = crear_respaldo(app, "paquete")
    if base is None:
        raise RuntimeError("No se encontró una base SQLite para respaldar.")

    carpeta_respaldos = Path(base).parent
    carpeta_respaldos.mkdir(parents=True, exist_ok=True)
    carpetas_archivos = [
        (Path(app.config["UPLOAD_FOLDER"]), Path("fotos")),
        (Path(app.config["BRAND_FOLDER"]), Path("personalizacion")),
        (Path(app.config["DOCUMENT_FOLDER"]), Path("comprobantes")),
    ]
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = carpeta_respaldos / f"academia_completo_{marca}.zip"
    temporal = destino.with_suffix(".zip.tmp")

    archivos = [(Path(base), "academia.db")]
    for carpeta, prefijo in carpetas_archivos:
        if carpeta.exists():
            archivos.extend(
                (ruta, (prefijo / ruta.relative_to(carpeta)).as_posix())
                for ruta in carpeta.rglob("*") if ruta.is_file()
            )

    manifiesto = {}
    try:
        with zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED) as paquete:
            for ruta, relativo in archivos:
                contenido = ruta.read_bytes()
                paquete.writestr(relativo, contenido)
                manifiesto[relativo] = hashlib.sha256(contenido).hexdigest()
            paquete.writestr(
                "manifiesto.json",
                json.dumps(
                    {"creado_en": datetime.now().isoformat(), "sha256": manifiesto},
                    indent=2,
                ),
            )
        temporal.replace(destino)
    except Exception:
        temporal.unlink(missing_ok=True)
        raise
    return destino
