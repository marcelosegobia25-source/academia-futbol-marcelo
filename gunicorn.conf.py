import os

# Render asigna el puerto mediante la variable de entorno PORT (normalmente 10000 o 5000)
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# En la capa gratuita de Render (512 MB de RAM), 1 worker con 4 threads
# previene caídas por sobreconsumo de memoria (OOM) y evita condiciones de carrera en migraciones
workers = int(os.environ.get("WEB_CONCURRENCY", 1))
threads = int(os.environ.get("PYTHON_THREADS", 4))
timeout = int(os.environ.get("WEB_TIMEOUT", 120))
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
