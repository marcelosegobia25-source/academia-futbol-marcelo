import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # host 0.0.0.0 opcional si se quiere acceder desde otro equipo en la misma red local.
    # Por defecto corre 100% local (offline) en http://127.0.0.1:5000
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(debug=debug, host="127.0.0.1", port=5000)
