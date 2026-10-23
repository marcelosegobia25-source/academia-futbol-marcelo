#!/usr/bin/env python3
"""Prueba la conexión a la base de datos configurada en .env"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import create_app
from app.extensions import db
from sqlalchemy import text

def test_db():
    print("=" * 70)
    print("PROBADOR DE CONEXIÓN A BASE DE DATOS")
    print("=" * 70)
    app = create_app()
    with app.app_context():
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        # Ocultar contraseña en pantalla
        masked_uri = uri
        if "@" in uri and "://" in uri:
            prefix, rest = uri.split("://", 1)
            creds, host_part = rest.split("@", 1)
            user = creds.split(":", 1)[0]
            masked_uri = f"{prefix}://{user}:******@{host_part}"
        print(f"🔗 Conectando a: {masked_uri}")
        
        try:
            res = db.session.execute(text("SELECT 1")).scalar()
            print("✅ Conexión exitosa a la base de datos (SELECT 1 OK)")
            
            # Consultar tablas existentes
            tablas = db.session.execute(text(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
                if "postgresql" in uri else
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            )).scalar()
            print(f"📊 Tablas encontradas en la base de datos: {tablas}")
            
            # Si hay tablas, verificar usuario admin
            if tablas > 0:
                try:
                    admin_count = db.session.execute(text("SELECT count(*) FROM usuario")).scalar()
                    print(f"👤 Usuarios registrados: {admin_count}")
                except Exception:
                    pass
            print("=" * 70)
            print("🎉 ¡TODO LISTO! La base de datos está perfectamente conectada y operativa.")
            print("=" * 70)
        except Exception as e:
            print("\n❌ Error al conectar:")
            print(f"   {e}")
            print("\n💡 Sugerencia:")
            print("   Verifica que la contraseña en el archivo .env sea la correcta.")
            print("   Si la contraseña tiene caracteres especiales (@, #, $, %), escríbelos URL-encoded.")

if __name__ == "__main__":
    test_db()
