"""Servidor local estable para el uso diario en Windows."""
from waitress import serve

from app import create_app


app = create_app()

if __name__ == "__main__":
    serve(app, host="127.0.0.1", port=5000, threads=4)
