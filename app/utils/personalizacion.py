import os

from flask import current_app

from app.models import Configuracion


def configuracion_y_logo():
    config = Configuracion.obtener()
    if not config.logo:
        return config, None
    ruta = os.path.join(current_app.config["BRAND_FOLDER"], config.logo)
    return config, ruta if os.path.isfile(ruta) else None
