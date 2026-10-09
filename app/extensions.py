from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def configurar_sqlite(dbapi_connection, connection_record):
    """Activa integridad y una concurrencia local más segura en SQLite."""
    modulo = dbapi_connection.__class__.__module__
    if not modulo.startswith("sqlite3"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()
