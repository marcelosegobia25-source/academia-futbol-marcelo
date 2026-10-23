FROM python:3.11-slim

# Evitar escritura de bytecode y habilitar buffer inmediato en stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

WORKDIR /app

# Instalar dependencias del sistema requeridas para compilación y utilidades
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear carpetas requeridas para archivos locales y logs
RUN mkdir -p instance/backups instance/branding instance/comprobantes instance/Descargas instance/logs instance/uploads

EXPOSE 5000

# Comando de inicio con Gunicorn
CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120"]
