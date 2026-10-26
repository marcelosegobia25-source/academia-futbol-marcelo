import os
import secrets
import sys
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass


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


def _obtener_database_uri():
    """Detecta y normaliza la URL de la base de datos (PostgreSQL / SQLite)."""
    if os.environ.get("USE_LOCAL_SQLITE", "").lower() in {"1", "true", "yes"}:
        ruta_db = os.path.join(INSTANCE_DIR, "academia.db").replace("\\", "/")
        return f"sqlite:///{ruta_db}"

    uri = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("NAME_OF_VARIABLE")
        or os.environ.get("DIRECT_URL")
        or os.environ.get("SUPABASE_DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or ""
    ).strip().strip("'\"")

    if not uri or "[TU_CONTRASEÑA]" in uri or "[YOUR-PASSWORD]" in uri:
        ruta_db = os.path.join(INSTANCE_DIR, "academia.db").replace("\\", "/")
        return f"sqlite:///{ruta_db}"
    if uri.startswith("sqlite"):
        if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////") and not (len(uri) > 11 and uri[10] == ":"):
            ruta_rel = uri.replace("sqlite:///", "", 1)
            ruta_abs = os.path.abspath(os.path.join(BASE_DIR, ruta_rel)).replace("\\", "/")
            return f"sqlite:///{ruta_abs}"
        return uri
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql+psycopg2://", 1)
    elif uri.startswith("postgresql://") and not uri.startswith("postgresql+"):
        uri = uri.replace("postgresql://", "postgresql+psycopg2://", 1)
    return uri


def _obtener_engine_options(database_uri):
    """Configura el pool de conexiones según el motor (PostgreSQL o SQLite)."""
    opciones = {"pool_pre_ping": True}
    if database_uri.startswith("sqlite"):
        opciones["connect_args"] = {"timeout": 5}
    else:
        # Configuración optimizada para PostgreSQL en la nube / producción
        opciones["connect_args"] = {
            "connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", 10)),
        }
        opciones["pool_size"] = int(os.environ.get("DB_POOL_SIZE", 10))
        opciones["max_overflow"] = int(os.environ.get("DB_MAX_OVERFLOW", 20))
        opciones["pool_recycle"] = int(os.environ.get("DB_POOL_RECYCLE", 300))
    return opciones


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or _clave_local()
    _db_uri = _obtener_database_uri()
    SQLALCHEMY_DATABASE_URI = _db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _obtener_engine_options(_db_uri)
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
    SESSION_COOKIE_SECURE = (
        os.environ.get("SESSION_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
        or bool(os.environ.get("RENDER"))
        or (
            bool(os.environ.get("DATABASE_URL"))
            and "postgresql" in os.environ.get("DATABASE_URL", "")
            and os.environ.get("USE_LOCAL_SQLITE", "").lower() not in {"1", "true", "yes"}
        )
    )
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    AUTH_REQUIRED = True
    WTF_CSRF_TIME_LIMIT = 8 * 60 * 60
    ITEMS_PER_PAGE = 40
    AUTO_BACKUP = True
    BACKUP_RETENTION_DAYS = 30

    # Días antes del vencimiento para marcar "Próximo a vencer"
    DIAS_PROXIMO_VENCIMIENTO = 5

    # Caché para activos estáticos locales (CSS, JS, iconos, fuentes)
    SEND_FILE_MAX_AGE_DEFAULT = int(os.environ.get("SEND_FILE_MAX_AGE_DEFAULT", 43200))
