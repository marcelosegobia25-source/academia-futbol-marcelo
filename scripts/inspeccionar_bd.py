import os
import sys
from pathlib import Path

BASE_DIR = r"c:\Users\Usuario\.gemini\antigravity-ide\scratch\academia-futbol-marcelo"
sys.path.insert(0, BASE_DIR)

from app import create_app
from app.extensions import db

app = create_app()

output_path = Path(BASE_DIR) / "scripts" / "tablas_info.txt"

with app.app_context():
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tablas = sorted(inspector.get_table_names())
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"TOTAL DE TABLAS: {len(tablas)}\n\n")
        for tabla in tablas:
            columnas = inspector.get_columns(tabla)
            f.write(f"==================================================\n")
            f.write(f"TABLA: {tabla}\n")
            f.write(f"==================================================\n")
            for col in columnas:
                not_null = "NOT NULL [Requerido]" if not col.get("nullable", True) else "NULL [Opcional]"
                tipo = str(col.get("type"))
                default = f" (Default: {col.get('default')})" if col.get("default") is not None else ""
                f.write(f"  • {col['name']:<25} | {tipo:<20} | {not_null}{default}\n")
            f.write("\n")

print(f"Información escrita en {output_path}")
