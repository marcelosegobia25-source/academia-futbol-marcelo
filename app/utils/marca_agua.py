import io

from PIL import Image


def imagen_con_opacidad(ruta: str, opacidad: float = 0.09) -> io.BytesIO:
    """Convierte el logo en una imagen tenue para utilizarla como marca de agua."""
    imagen = Image.open(ruta).convert("RGBA")
    alpha = imagen.getchannel("A").point(lambda valor: round(valor * opacidad))
    imagen.putalpha(alpha)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer
