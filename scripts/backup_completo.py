"""Crea un paquete ZIP con base, fotografías y manifiesto de verificación."""

from app import create_app
from app.utils.backup import crear_respaldo_completo


app = create_app()
with app.app_context():
    destino = crear_respaldo_completo(app)

print(f"Respaldo completo creado: {destino}")
