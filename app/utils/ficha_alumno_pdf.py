import io
import math
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from PIL import Image, ImageOps


ROJO = colors.HexColor("#d40b12")
NEGRO = colors.HexColor("#101214")
GRIS = colors.HexColor("#687078")
LINEA = colors.HexColor("#e3e5e7")
FONDO = colors.HexColor("#f5f6f7")


def _texto_ajustado(texto, fuente, tamano, ancho):
    texto = str(texto or "-")
    if stringWidth(texto, fuente, tamano) <= ancho:
        return texto
    while texto and stringWidth(texto + "...", fuente, tamano) > ancho:
        texto = texto[:-1]
    return texto.rstrip() + "..."


def _tamano_para_encajar(texto, fuente, tamano_maximo, tamano_minimo, ancho):
    """Reduce la fuente antes de truncar datos relevantes como el equipo."""
    texto = str(texto or "-")
    tamano = float(tamano_maximo)
    while tamano > tamano_minimo and stringWidth(texto, fuente, tamano) > ancho:
        tamano -= 0.25
    return max(tamano, tamano_minimo)


def _imagen_cubierta(c, ruta, x, y, ancho, alto, circular=False, recortar=False):
    if recortar:
        temporal = io.BytesIO()
        with Image.open(ruta) as origen:
            cuadrada = ImageOps.fit(
                origen.convert("RGB"), (600, 600),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            cuadrada.save(temporal, format="JPEG", quality=92)
        temporal.seek(0)
        imagen = ImageReader(temporal)
    else:
        imagen = ImageReader(ruta)
    iw, ih = imagen.getSize()
    escala = max(ancho / iw, alto / ih)
    dw, dh = iw * escala, ih * escala
    dx, dy = x + (ancho - dw) / 2, y + (alto - dh) / 2
    c.saveState()
    if circular:
        trazado = c.beginPath()
        trazado.circle(x + ancho / 2, y + alto / 2, min(ancho, alto) / 2)
        c.clipPath(trazado, stroke=0, fill=0)
    c.drawImage(imagen, dx, dy, width=dw, height=dh, preserveAspectRatio=True, mask="auto")
    c.restoreState()


def _titulo_seccion(c, x, y, ancho, titulo):
    c.setFillColor(NEGRO)
    c.roundRect(x, y - 23, ancho, 23, 4, fill=1, stroke=0)
    c.setFillColor(ROJO)
    c.rect(x, y - 23, 7, 23, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(x + 16, y - 15, titulo.upper())
    return y - 31


def _dibujar_icono(c, cx, cy, tipo):
    """Iconos vectoriales sencillos, legibles y compatibles con impresión."""
    c.saveState()
    c.setStrokeColor(colors.white)
    c.setFillColor(colors.white)
    c.setLineWidth(0.9)
    tipo = tipo or "id"
    if tipo == "calendario":
        c.roundRect(cx - 3.8, cy - 3.1, 7.6, 6.2, 0.8, fill=0, stroke=1)
        c.line(cx - 3.8, cy + 1.2, cx + 3.8, cy + 1.2)
        c.line(cx - 2.1, cy + 4, cx - 2.1, cy + 2.1)
        c.line(cx + 2.1, cy + 4, cx + 2.1, cy + 2.1)
    elif tipo == "ubicacion":
        c.circle(cx, cy + 1, 2.5, fill=0, stroke=1)
        c.circle(cx, cy + 1, 0.7, fill=1, stroke=0)
        c.line(cx - 1.8, cy - 0.8, cx, cy - 4)
        c.line(cx + 1.8, cy - 0.8, cx, cy - 4)
    elif tipo == "telefono":
        c.line(cx - 3.2, cy + 3.3, cx - 1.5, cy + 1.5)
        c.line(cx - 1.5, cy + 1.5, cx + 1.3, cy - 1.2)
        c.line(cx + 1.3, cy - 1.2, cx + 3.2, cy - 3.1)
        c.line(cx - 3.2, cy + 3.3, cx - 2, cy + 4)
        c.line(cx + 3.2, cy - 3.1, cx + 4, cy - 1.9)
    elif tipo in {"persona", "sexo"}:
        c.circle(cx, cy + 2.1, 1.8, fill=1, stroke=0)
        c.arc(cx - 3.8, cy - 4.2, cx + 3.8, cy + 0.5, 15, 150)
    elif tipo == "peso":
        c.roundRect(cx - 4, cy - 3.5, 8, 7, 1.2, fill=0, stroke=1)
        c.arc(cx - 2, cy - 0.5, cx + 2, cy + 3.2, 20, 140)
        c.line(cx, cy + 1.2, cx + 1.2, cy + 2.4)
    elif tipo == "altura":
        c.line(cx - 2.5, cy - 4, cx - 2.5, cy + 4)
        for paso in (-3, -1, 1, 3):
            c.line(cx - 2.5, cy + paso, cx + (1.5 if paso % 2 else 0.5), cy + paso)
    elif tipo == "estrella":
        puntos = []
        for indice in range(10):
            angulo = math.radians(90 + indice * 36)
            radio = 4 if indice % 2 == 0 else 1.8
            puntos.append((cx + radio * math.cos(angulo), cy + radio * math.sin(angulo)))
        trazado = c.beginPath()
        trazado.moveTo(*puntos[0])
        for punto in puntos[1:]:
            trazado.lineTo(*punto)
        trazado.close()
        c.drawPath(trazado, fill=1, stroke=0)
    elif tipo in {"balon", "posicion"}:
        c.circle(cx, cy, 3.8, fill=0, stroke=1)
        c.circle(cx, cy, 1.2, fill=0, stroke=1)
        for angulo in range(0, 360, 72):
            rad = math.radians(angulo)
            c.line(cx + 1.1 * math.cos(rad), cy + 1.1 * math.sin(rad), cx + 3.5 * math.cos(rad), cy + 3.5 * math.sin(rad))
    elif tipo == "equipo":
        trazado = c.beginPath()
        trazado.moveTo(cx - 4, cy + 2)
        trazado.lineTo(cx - 2, cy + 4)
        trazado.lineTo(cx - 0.8, cy + 2.5)
        trazado.lineTo(cx + 0.8, cy + 2.5)
        trazado.lineTo(cx + 2, cy + 4)
        trazado.lineTo(cx + 4, cy + 2)
        trazado.lineTo(cx + 2.5, cy)
        trazado.lineTo(cx + 2.5, cy - 4)
        trazado.lineTo(cx - 2.5, cy - 4)
        trazado.lineTo(cx - 2.5, cy)
        trazado.close()
        c.drawPath(trazado, fill=0, stroke=1)
    elif tipo == "pierna":
        c.line(cx - 2.5, cy + 4, cx - 0.5, cy - 1.5)
        c.line(cx - 0.5, cy - 1.5, cx + 3.5, cy - 3)
        c.line(cx + 3.5, cy - 3, cx + 4, cy - 1.5)
        c.line(cx + 4, cy - 1.5, cx + 0.8, cy)
    elif tipo == "categoria":
        trazado = c.beginPath()
        trazado.moveTo(cx, cy + 4)
        trazado.lineTo(cx + 3.5, cy + 2.3)
        trazado.lineTo(cx + 2.7, cy - 2.2)
        trazado.lineTo(cx, cy - 4)
        trazado.lineTo(cx - 2.7, cy - 2.2)
        trazado.lineTo(cx - 3.5, cy + 2.3)
        trazado.close()
        c.drawPath(trazado, fill=0, stroke=1)
    else:
        c.rect(cx - 4, cy - 3, 8, 6, fill=0, stroke=1)
        c.circle(cx - 2.2, cy + 0.8, 0.9, fill=1, stroke=0)
        c.line(cx - 0.5, cy + 1.2, cx + 2.8, cy + 1.2)
        c.line(cx - 0.5, cy - 1, cx + 2.8, cy - 1)
    c.restoreState()


def _fila_dato(c, x, y, ancho, etiqueta, valor, icono="id"):
    c.setFillColor(ROJO)
    c.circle(x + 8, y - 6, 7, fill=1, stroke=0)
    _dibujar_icono(c, x + 8, y - 6, icono)
    c.setFillColor(GRIS)
    c.setFont("Helvetica-Bold", 8.2)
    c.drawString(x + 23, y - 3, etiqueta.upper())
    c.setFillColor(NEGRO)
    c.setFont("Helvetica", 10.5)
    valor = _texto_ajustado(valor, "Helvetica", 10.5, ancho - 142)
    c.drawString(x + 132, y - 3, valor)
    c.setStrokeColor(LINEA)
    c.line(x + 23, y - 15, x + ancho, y - 15)
    return y - 32


def _dato_compacto(c, x, y, etiqueta, valor, ancho=76):
    c.setFillColor(GRIS)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x, y, etiqueta.upper())
    c.setFillColor(NEGRO)
    tamano = _tamano_para_encajar(valor, "Helvetica-Bold", 9, 6.5, ancho)
    c.setFont("Helvetica-Bold", tamano)
    c.drawString(x, y - 13, _texto_ajustado(valor, "Helvetica-Bold", tamano, ancho))


def generar_ficha_alumno(
    alumno, logo_path=None, foto_path=None, gestion=None,
    nombre_academia="Mi Academia Deportiva", eslogan=None,
):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    ancho, alto = LETTER

    c.setFillColor(colors.white)
    c.rect(0, 0, ancho, alto, fill=1, stroke=0)

    # Encabezado institucional
    c.setFillColor(NEGRO)
    c.rect(0, alto - 112, ancho, 112, fill=1, stroke=0)
    c.setFillColor(ROJO)
    p = c.beginPath()
    p.moveTo(392, alto)
    p.lineTo(ancho, alto)
    p.lineTo(ancho, alto - 112)
    p.lineTo(360, alto - 112)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # Fondo blanco compacto para que la corona, el borde negro y los textos
    # del escudo transparente se distingan sobre el encabezado oscuro.
    if logo_path and os.path.isfile(logo_path):
        c.setFillColor(colors.white)
        c.rect(16, alto - 103, 68, 92, fill=1, stroke=0)
        _imagen_cubierta(c, logo_path, 18, alto - 101, 64, 88)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#c8c8c8"))
    c.drawString(94, alto - 34, "ACADEMIA DEPORTIVA")
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.white)
    c.drawString(92, alto - 59, _texto_ajustado(nombre_academia.upper(), "Helvetica-Bold", 18, 250))
    c.setFont("Helvetica", 6.3)
    c.setFillColor(colors.HexColor("#d0d0d0"))
    c.drawString(93, alto - 78, _texto_ajustado(eslogan or "GESTIÓN DEPORTIVA INTEGRAL", "Helvetica", 6.3, 250))

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(491, alto - 48, "FICHA DEL ALUMNO")
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(491, alto - 69, f"TEMPORADA {gestion or date.today().year}")

    # Tarjeta izquierda: identidad
    lx, ly, lw, lh = 22, 82, 190, 576
    c.setFillColor(colors.white)
    c.setStrokeColor(LINEA)
    c.roundRect(lx, ly, lw, lh, 8, fill=1, stroke=1)

    foto_x, foto_y, foto_t = lx + 20, 495, 150
    c.setFillColor(colors.HexColor("#e8eaec"))
    c.roundRect(foto_x - 3, foto_y - 3, foto_t + 6, foto_t + 6, 7, fill=1, stroke=0)
    if foto_path and os.path.exists(foto_path):
        _imagen_cubierta(
            c, foto_path, foto_x, foto_y, foto_t, foto_t, recortar=True
        )
    else:
        c.setFillColor(colors.HexColor("#c8cdd1"))
        c.circle(foto_x + foto_t / 2, foto_y + 91, 28, fill=1, stroke=0)
        c.roundRect(foto_x + 36, foto_y + 18, 78, 55, 24, fill=1, stroke=0)
    c.setStrokeColor(NEGRO)
    c.setLineWidth(2)
    c.rect(foto_x - 2, foto_y - 2, foto_t + 4, foto_t + 4, fill=0, stroke=1)

    nombre = alumno.nombre_completo.upper()
    tamano_nombre = 16
    while tamano_nombre > 10 and stringWidth(nombre, "Helvetica-Bold", tamano_nombre) > lw - 22:
        tamano_nombre -= 1
    c.setFillColor(NEGRO)
    c.setFont("Helvetica-Bold", tamano_nombre)
    c.drawCentredString(lx + lw / 2, 474, nombre)
    c.setFillColor(ROJO)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(lx + lw / 2, 460, "JUGADOR/A")

    c.setFillColor(NEGRO if alumno.estado == "Activo" else GRIS)
    c.roundRect(lx + 20, 424, lw - 40, 24, 4, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(lx + lw / 2, 432, alumno.estado.upper())

    _dato_compacto(c, lx + 20, 407, "Edad", f"{alumno.edad} años", 60)
    equipos = ", ".join(e.nombre for e in alumno.equipos) or "Sin equipo"
    _dato_compacto(c, lx + 104, 407, "Equipo", equipos, 70)

    c.setStrokeColor(ROJO)
    c.line(lx + 18, 376, lx + lw - 18, 376)
    campos_izq = [
        ("ID alumno", f"ALU-{alumno.id_alumno:04d}", "id"),
        ("Categoría", alumno.categoria.nombre if alumno.categoria else "Sin categoría", "categoria"),
        ("Posición", alumno.posicion or "-", "posicion"),
        ("Pierna hábil", alumno.pierna_habil or "-", "pierna"),
        ("Fecha de nacimiento", alumno.fecha_nacimiento.strftime("%d/%m/%Y"), "calendario"),
        ("Sexo", alumno.sexo or "-", "sexo"),
    ]
    y = 357
    for etiqueta, valor, icono in campos_izq:
        c.setFillColor(ROJO)
        c.circle(lx + 27, y + 1, 9, fill=1, stroke=0)
        _dibujar_icono(c, lx + 27, y + 1, icono)
        c.setFillColor(GRIS)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(lx + 44, y + 6, etiqueta.upper())
        c.setFillColor(NEGRO)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(lx + 44, y - 9, _texto_ajustado(valor, "Helvetica-Bold", 10, lw - 66))
        c.setStrokeColor(LINEA)
        c.line(lx + 44, y - 17, lx + lw - 18, y - 17)
        y -= 47

    # Columna derecha
    rx, rw = 230, 360
    c.setFillColor(colors.white)
    c.setStrokeColor(LINEA)
    c.roundRect(rx, 326, rw, 332, 8, fill=1, stroke=1)
    y = _titulo_seccion(c, rx, 650, rw, "Datos personales")
    datos = [
        ("CI", alumno.ci or "-", "id"),
        ("Fecha de nacimiento", alumno.fecha_nacimiento.strftime("%d/%m/%Y"), "calendario"),
        ("Dirección", alumno.direccion or "-", "ubicacion"),
        ("Teléfono", alumno.telefono or "-", "telefono"),
        ("Tutor", alumno.tutor or "-", "persona"),
        ("Tutor 2", alumno.tutor2 or "-", "persona"),
        ("Peso", f"{alumno.peso} kg" if alumno.peso else "-", "peso"),
        ("Estatura", f"{alumno.estatura} m" if alumno.estatura else "-", "altura"),
        ("Beca", alumno.beca or "Ninguna", "estrella"),
    ]
    for etiqueta, valor, icono in datos:
        y = _fila_dato(c, rx + 14, y, rw - 28, etiqueta, valor, icono)

    c.setFillColor(colors.white)
    c.setStrokeColor(LINEA)
    c.roundRect(rx, 82, rw, 226, 8, fill=1, stroke=1)
    _titulo_seccion(c, rx, 300, rw, "Información deportiva")
    c.setFillColor(FONDO)
    c.roundRect(rx + 14, 102, 150, 157, 5, fill=1, stroke=0)
    c.roundRect(rx + 176, 102, 170, 157, 5, fill=1, stroke=0)
    c.setFillColor(GRIS)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(rx + 25, 242, "EQUIPO ACTUAL")
    c.drawString(rx + 187, 242, "CARACTERÍSTICAS")
    c.setFillColor(ROJO)
    c.circle(rx + 89, 198, 18, fill=1, stroke=0)
    _dibujar_icono(c, rx + 89, 198, "equipo")
    c.setFillColor(NEGRO)
    tamano_equipo = _tamano_para_encajar(equipos, "Helvetica-Bold", 13, 7.5, 132)
    c.setFont("Helvetica-Bold", tamano_equipo)
    c.drawCentredString(
        rx + 89,
        165,
        _texto_ajustado(equipos, "Helvetica-Bold", tamano_equipo, 132),
    )

    caracteristicas = [
        ("Posición", alumno.posicion or "-", "posicion"),
        ("Pierna hábil", alumno.pierna_habil or "-", "pierna"),
        ("Categoría", alumno.categoria.nombre if alumno.categoria else "-", "categoria"),
    ]
    cy = 216
    for etiqueta, valor, icono in caracteristicas:
        c.setFillColor(ROJO)
        c.circle(rx + 193, cy, 8, fill=1, stroke=0)
        _dibujar_icono(c, rx + 193, cy, icono)
        c.setFillColor(GRIS)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(rx + 207, cy + 3, etiqueta.upper())
        c.setFillColor(NEGRO)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(rx + 207, cy - 10, _texto_ajustado(valor, "Helvetica-Bold", 10, 125))
        cy -= 46

    c.setFillColor(colors.HexColor("#7b8085"))
    c.setFont("Helvetica", 6.5)
    c.drawRightString(ancho - 22, 24, f"Ficha generada el {date.today().strftime('%d/%m/%Y')}")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
