import io
from functools import lru_cache
from PIL import Image
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader


@lru_cache(maxsize=8)
def _logo_optimizado(ruta):
    with Image.open(ruta) as original:
        imagen = original.convert("RGBA")
        imagen.thumbnail((320, 320), Image.Resampling.LANCZOS)
        salida = io.BytesIO()
        imagen.save(salida, "PNG", optimize=True)
        return salida.getvalue()


def _dibujar_logo(c, ruta, x, y, ancho_max, alto_max):
    imagen = ImageReader(io.BytesIO(_logo_optimizado(ruta)))
    ancho_imagen, alto_imagen = imagen.getSize()
    escala = min(ancho_max / ancho_imagen, alto_max / alto_imagen)
    ancho = ancho_imagen * escala
    alto = alto_imagen * escala
    c.drawImage(
        imagen, x + (ancho_max - ancho) / 2, y + (alto_max - alto) / 2,
        width=ancho, height=alto, preserveAspectRatio=True, mask="auto",
    )


def generar_recibo_pago(
    pago, alumno, logo_path=None, nombre_academia="Mi Academia Deportiva", es_copia=False
) -> io.BytesIO:
    """Genera un recibo de pago en PDF (tamaño A5) listo para imprimir."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A5)
    ancho, alto = A5
    if es_copia:
        c.saveState()
        c.setFillColor(colors.Color(0.75, 0.75, 0.75, alpha=0.22))
        c.setFont("Helvetica-Bold", 38)
        c.translate(ancho / 2, alto / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, "COPIA")
        c.restoreState()

    # Encabezado institucional con ambos escudos.
    if logo_path:
        _dibujar_logo(c, logo_path, 15.4 * mm, alto - 39 * mm, 19.2 * mm, 22.4 * mm)

    y = alto - 18 * mm
    c.setFillColor(colors.HexColor("#17231f"))
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(ancho / 2, y, "RECIBO DE PAGO")
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(ancho / 2, y, nombre_academia.upper()[:60])
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawCentredString(ancho / 2, y, "Pago de mensualidad")
    y -= 10 * mm
    c.setLineWidth(0.5)
    c.line(15 * mm, y, ancho - 15 * mm, y)

    y -= 10 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15 * mm, y, f"Recibo N°: {pago.id_pago:06d}")
    y -= 7 * mm
    c.setFont("Helvetica", 10)

    filas = [
        ("Alumno:", alumno.nombre_completo),
        ("CI:", alumno.ci or "-"),
        ("Categoría:", alumno.categoria.nombre if alumno.categoria else "-"),
        ("Mes pagado:", pago.mes_pagado),
        ("Fecha de pago:", pago.fecha_pago.strftime("%d/%m/%Y")),
        ("Hora de registro:", pago.hora_registro.strftime("%H:%M") if pago.hora_registro else "-"),
        ("Fecha de vencimiento:", pago.fecha_vencimiento.strftime("%d/%m/%Y")),
        ("Modo de pago:", "Cubierto por beca" if pago.es_beca else pago.modo_pago),
        ("Operación QR:", pago.numero_operacion or "-"),
        ("Monto pagado:", f"{pago.monto:.2f}"),
        ("Estado:", pago.estado),
    ]
    for etiqueta, valor in filas:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15 * mm, y, etiqueta)
        c.setFont("Helvetica", 10)
        c.drawString(55 * mm, y, str(valor))
        y -= 7 * mm

    y -= 10 * mm
    c.line(15 * mm, y, ancho - 15 * mm, y)
    y -= 8 * mm
    c.setFont("Helvetica-Oblique", 8)
    leyenda = "COPIA DEL COMPROBANTE" if es_copia else "Documento original generado automáticamente. Conserve este comprobante."
    c.drawCentredString(ancho / 2, y, leyenda)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
