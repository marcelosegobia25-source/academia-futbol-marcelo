import os
import secrets
import sys
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _directorio_datos():
    """Mantiene los datos persistentes fuera del ejecutable instalado."""
    configurado = os.environ.get("ACADEMIA_DATA_DIR")
    if configurado:
        return os.path.abspath(os.path.expandvars(configurado))
    if getattr(sys, "frozen", False):
        raiz = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(raiz, "GestionAcademiaDeportiva")
    return os.path.join(BASE_DIR, "instance")


INSTANCE_DIR = _directorio_datos()


def _clave_local():
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    ruta = os.path.join(INSTANCE_DIR, ".secret_key")
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as archivo:
            return archivo.read().strip()
    clave = secrets.token_hex(32)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(clave)
    return clave


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or _clave_local()
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(INSTANCE_DIR, "academia.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "connect_args": {"timeout": 5}}
    UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, "uploads", "alumnos")
    BRAND_FOLDER = os.path.join(INSTANCE_DIR, "branding")
    DOCUMENT_FOLDER = os.path.join(INSTANCE_DIR, "comprobantes")
    LEGACY_UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads", "alumnos")
    EXPORT_FOLDER = os.path.join(BASE_DIR, "app", "static", "exports")
    DOWNLOAD_FOLDER = os.path.join(INSTANCE_DIR, "Descargas")
    LOG_FOLDER = os.path.join(INSTANCE_DIR, "logs")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB para fotos
    ALLOWED_PHOTO_EXT = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_DOCUMENT_EXT = {"pdf", "png", "jpg", "jpeg", "webp"}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "gestion_academia_session"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    AUTH_REQUIRED = True
    WTF_CSRF_TIME_LIMIT = 8 * 60 * 60
    ITEMS_PER_PAGE = 40
    AUTO_BACKUP = True
    BACKUP_RETENTION_DAYS = 30

    # Días antes del vencimiento para marcar "Próximo a vencer"
    DIAS_PROXIMO_VENCIMIENTO = 5
