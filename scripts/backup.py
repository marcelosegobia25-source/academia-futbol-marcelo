from app import create_app
from app.utils.backup import crear_respaldo


app = create_app()
with app.app_context():
    ruta = crear_respaldo(app, "manual")
    print(f"Respaldo creado: {ruta}")
