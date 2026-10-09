"""Punto de entrada para la aplicación de escritorio instalada en Windows."""
import os
import socket
import threading
import webbrowser

from waitress import serve

from app import create_app


HOST = "127.0.0.1"
PORT = int(os.environ.get("ACADEMIA_PORT", "5000"))
URL = f"http://{HOST}:{PORT}"


def _puerto_en_uso():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as comprobador:
        comprobador.settimeout(0.4)
        return comprobador.connect_ex((HOST, PORT)) == 0


def main():
    if _puerto_en_uso():
        if not os.environ.get("ACADEMIA_NO_BROWSER"):
            webbrowser.open(URL)
        return

    app = create_app()
    if not os.environ.get("ACADEMIA_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(URL)).start()
    serve(app, host=HOST, port=PORT, threads=4)


if __name__ == "__main__":
    main()
