import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # host 0.0.0.0 opcional si se quiere acceder desde otro equipo en la misma red local.
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, host=host, port=port)
