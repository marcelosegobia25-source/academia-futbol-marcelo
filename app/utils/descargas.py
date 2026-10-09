"""Almacenamiento centralizado de documentos generados por la plataforma."""
import io
import os
import shutil
from datetime import datetime
from pathlib import Path

from flask import current_app, send_file
from werkzeug.utils import secure_filename


CATEGORIAS = {
    "recibos": "Pagos/Recibos",
    "reportes_pagos": "Pagos/Reportes",
    "alumnos": "Alumnos/Listados",
    "perfiles": "Alumnos/Perfiles",
    "partidos": "Partidos",
    "calendarios": "Calendarios",
    "campeonatos": "Campeonatos",
    "respaldos": "Respaldos",
}


def carpeta_descargas():
    ruta = Path(current_app.config["DOWNLOAD_FOLDER"]).resolve()
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def _carpeta_categoria(categoria):
    relativa = CATEGORIAS.get(categoria)
    if relativa is None:
        raise ValueError(f"Categoría de descarga no válida: {categoria}")
    destino = carpeta_descargas().joinpath(*relativa.split("/"))
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _destino_disponible(carpeta, nombre):
    nombre_seguro = secure_filename(nombre)
    if not nombre_seguro:
        raise ValueError("El nombre de descarga no es válido.")
    destino = carpeta / nombre_seguro
    if not destino.exists():
        return destino
    marca = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return carpeta / f"{destino.stem}_{marca}{destino.suffix}"


def guardar_buffer(buffer, categoria, nombre):
    destino = _destino_disponible(_carpeta_categoria(categoria), nombre)
    posicion = buffer.tell()
    buffer.seek(0)
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    try:
        with temporal.open("wb") as archivo:
            shutil.copyfileobj(buffer, archivo)
        os.replace(temporal, destino)
    finally:
        temporal.unlink(missing_ok=True)
        buffer.seek(posicion)
    current_app.logger.info("Documento guardado en Descargas: %s", destino)
    return destino


def guardar_texto(contenido, categoria, nombre, encoding="utf-8"):
    buffer = io.BytesIO(contenido.encode(encoding))
    return guardar_buffer(buffer, categoria, nombre)


def guardar_archivo(origen, categoria, nombre=None):
    origen = Path(origen)
    destino = _destino_disponible(
        _carpeta_categoria(categoria), nombre or origen.name
    )
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    try:
        shutil.copy2(origen, temporal)
        os.replace(temporal, destino)
    finally:
        temporal.unlink(missing_ok=True)
    current_app.logger.info("Documento copiado a Descargas: %s", destino)
    return destino


def enviar_buffer(buffer, categoria, nombre, mimetype):
    guardar_buffer(buffer, categoria, nombre)
    buffer.seek(0)
    return send_file(
        buffer, mimetype=mimetype, as_attachment=True, download_name=nombre
    )
