import io
from xml.sax.saxutils import escape, quoteattr
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, LongTable, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader

from app.utils.marca_agua import imagen_con_opacidad


def _es_columna_numeracion(encabezado) -> bool:
    texto = str(encabezado or "").strip().lower()
    return texto.startswith("n") and len(texto) <= 4


def _parrafo_celda(valor, estilo):
    texto = str(valor if valor is not None else "")
    if texto.lower().startswith(("http://", "https://")):
        return Paragraph(
            f'<link href={quoteattr(texto)} color="#0b57d0"><u>Abrir Google Maps</u></link>',
            estilo,
        )
    return Paragraph(escape(texto), estilo)


def generar_tabla_pdf(
    titulo: str, encabezados: list, filas: list, orientacion="horizontal",
    tamano_pagina="a4", tamano_letra=8, logo_path=None,
) -> io.BytesIO:
    """Genera un PDF genérico con una tabla, usado para exportar listados
    (alumnos, pagos, convocatorias) respetando los filtros aplicados."""
    buffer = io.BytesIO()
    pagina_base = LETTER if tamano_pagina.lower() == "carta" else A4
    # Con muchas columnas la orientación vertical termina comprimiendo tanto
    # las celdas que el contenido parece solapado.
    usar_horizontal = orientacion == "horizontal" or len(encabezados) > 5
    pagesize = landscape(pagina_base) if usar_horizontal else pagina_base
    if len(encabezados) > 8:
        tamano_letra = min(tamano_letra, 7)
    doc = SimpleDocTemplate(
        buffer, pagesize=pagesize, topMargin=12 * mm, bottomMargin=12 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
    )
    estilos = getSampleStyleSheet()

    elementos = [
        Paragraph(escape(str(titulo or "Reporte")), estilos["Title"]),
        Spacer(1, 6 * mm),
    ]

    estilo_celda = ParagraphStyle(
        "CeldaTabla", parent=estilos["BodyText"], fontName="Helvetica",
        fontSize=tamano_letra, leading=tamano_letra * 1.2, spaceAfter=0,
    )
    estilo_cabecera = ParagraphStyle(
        "CabeceraTabla", parent=estilo_celda, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=1,
    )

    # Calcula anchos proporcionales por contenido y los normaliza al ancho útil.
    # La tabla siempre cabe en la hoja; el texto largo se distribuye en líneas.
    pesos = []
    for indice, encabezado in enumerate(encabezados):
        valores = [str(encabezado)] + [str(fila[indice]) if indice < len(fila) else "" for fila in filas[:80]]
        pesos.append(max(8, min(28, max(len(valor) for valor in valores))))
    if encabezados and _es_columna_numeracion(encabezados[0]):
        valores_numero = [str(encabezados[0])] + [str(fila[0]) for fila in filas if fila]
        ancho_numero = max(stringWidth(valor, "Helvetica", tamano_letra) for valor in valores_numero) + 4 * mm
        ancho_numero = max(8 * mm, min(13 * mm, ancho_numero))
        pesos_restantes = pesos[1:]
        total_restante = sum(pesos_restantes) or 1
        ancho_restante = doc.width - ancho_numero
        anchos = [ancho_numero] + [ancho_restante * peso / total_restante for peso in pesos_restantes]
    else:
        total_pesos = sum(pesos) or 1
        anchos = [doc.width * peso / total_pesos for peso in pesos]

    data = [[Paragraph(escape(str(valor)), estilo_cabecera) for valor in encabezados]]
    data.extend([
        [
            _parrafo_celda(
                fila[indice] if indice < len(fila) else "",
                estilo_celda,
            )
            for indice in range(len(encabezados))
        ]
        for fila in filas
    ])
    tabla = LongTable(data, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#198754")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), tamano_letra),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ]))
    if encabezados and _es_columna_numeracion(encabezados[0]):
        tabla.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (0, -1), 2),
            ("RIGHTPADDING", (0, 0), (0, -1), 2),
        ]))
    elementos.append(tabla)

    marca_agua = ImageReader(imagen_con_opacidad(logo_path, 0.08)) if logo_path else None

    def dibujar_marca_agua(canvas, documento):
        if marca_agua is None:
            return
        pagina_ancho, pagina_alto = documento.pagesize
        imagen_ancho, imagen_alto = marca_agua.getSize()
        escala = min((pagina_ancho * 0.45) / imagen_ancho, (pagina_alto * 0.48) / imagen_alto)
        ancho_marca = imagen_ancho * escala
        alto_marca = imagen_alto * escala
        canvas.saveState()
        canvas.drawImage(
            marca_agua,
            (pagina_ancho - ancho_marca) / 2,
            (pagina_alto - alto_marca) / 2,
            width=ancho_marca,
            height=alto_marca,
            preserveAspectRatio=True,
            mask="auto",
        )
        canvas.restoreState()

    if marca_agua is not None:
        # afterPage dibuja al final de cada página: la tabla no tapa la marca,
        # mientras que la transparencia mantiene todo el texto legible.
        doc.afterPage = lambda: dibujar_marca_agua(doc.canv, doc)
    doc.build(elementos)
    buffer.seek(0)
    return buffer
