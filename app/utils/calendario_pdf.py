import io
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


COLOR_TIPO = {
    "Partido": "#3455A4",
    "Entrenamiento": "#C47A00",
    "Campeonato": "#20734C",
    "Evento": "#277A8A",
}
DIA_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _texto_item(item):
    hora = item["hora"].strftime("%H:%M") if item.get("hora") else "Todo el día"
    lugar = f" - {item['lugar']}" if item.get("lugar") else ""
    return f"<b>{hora}</b> | {item['texto']}{lugar}"


def generar_calendario_pdf(titulo, inicio, fin, items, vista="mensual"):
    buffer = io.BytesIO()
    estilos = getSampleStyleSheet()
    pagina = landscape(A4) if vista == "mensual" else A4
    doc = SimpleDocTemplate(
        buffer, pagesize=pagina, topMargin=12 * mm, bottomMargin=12 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
        title=titulo,
    )
    titulo_estilo = ParagraphStyle(
        "TituloCalendario", parent=estilos["Title"], textColor=colors.HexColor("#173F32"),
        fontSize=20, leading=24, spaceAfter=4 * mm,
    )
    subtitulo_estilo = ParagraphStyle(
        "SubtituloCalendario", parent=estilos["BodyText"], textColor=colors.HexColor("#52605A"),
        fontSize=9, leading=12, spaceAfter=5 * mm,
    )
    celda_estilo = ParagraphStyle(
        "CeldaCalendario", parent=estilos["BodyText"], fontSize=6.7, leading=8.2,
        textColor=colors.HexColor("#26323F"), spaceAfter=1.2 * mm,
    )
    dia_estilo = ParagraphStyle(
        "DiaCalendario", parent=celda_estilo, fontName="Helvetica-Bold",
        fontSize=9, leading=11, textColor=colors.HexColor("#173F32"),
    )
    elementos = [
        Paragraph(titulo, titulo_estilo),
        Paragraph(
            f"Periodo: {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')}",
            subtitulo_estilo,
        ),
    ]
    por_fecha = defaultdict(list)
    for item in items:
        por_fecha[item["fecha"]].append(item)

    if vista == "semanal":
        encabezados = ["Fecha", "Hora", "Tipo", "Actividad", "Lugar", "Categoría / Equipo"]
        filas = []
        fecha = inicio
        while fecha <= fin:
            actividades = por_fecha.get(fecha, [])
            if actividades:
                for item in actividades:
                    filas.append([
                        f"{DIA_ES[fecha.weekday()]}\n{fecha.strftime('%d/%m/%Y')}",
                        item["hora"].strftime("%H:%M") if item.get("hora") else "Todo el día",
                        item["tipo"], item["texto"], item.get("lugar") or "-",
                        " / ".join(v for v in (item.get("categoria"), item.get("equipo")) if v) or "-",
                    ])
            else:
                filas.append([
                    f"{DIA_ES[fecha.weekday()]}\n{fecha.strftime('%d/%m/%Y')}",
                    "-", "-", "Sin actividades", "-", "-",
                ])
            fecha = fecha.fromordinal(fecha.toordinal() + 1)
        cabecera_estilo = ParagraphStyle(
            "CabeceraSemanal", parent=celda_estilo, textColor=colors.white,
            fontName="Helvetica-Bold",
        )
        data = [[Paragraph(h, cabecera_estilo) for h in encabezados]]
        data += [[Paragraph(str(valor).replace("\n", "<br/>"), celda_estilo) for valor in fila] for fila in filas]
        tabla = LongTable(
            data, colWidths=[28 * mm, 19 * mm, 23 * mm, 57 * mm, 38 * mm, 32 * mm],
            repeatRows=1,
        )
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173F32")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#BCC9C2")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7F4")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabla)
    else:
        dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        semanas = []
        semana = [None] * inicio.weekday()
        fecha = inicio
        while fecha <= fin:
            semana.append(fecha)
            if len(semana) == 7:
                semanas.append(semana)
                semana = []
            fecha = fecha.fromordinal(fecha.toordinal() + 1)
        if semana:
            semanas.append(semana + [None] * (7 - len(semana)))
        data = [[Paragraph(f"<b>{dia}</b>", ParagraphStyle(
            f"Cab{dia}", parent=celda_estilo, alignment=TA_CENTER, textColor=colors.white
        )) for dia in dias_semana]]
        for semana in semanas:
            fila = []
            for fecha in semana:
                if fecha is None:
                    fila.append("")
                    continue
                partes = [f"<b>{fecha.day}</b>", "<br/>"]
                for item in por_fecha.get(fecha, [])[:2]:
                    color = COLOR_TIPO.get(item["tipo"], "#52605A")
                    partes.append(f'<br/><font color="{color}">{_texto_item(item)}</font>')
                restantes = len(por_fecha.get(fecha, [])) - 2
                if restantes > 0:
                    partes.append(f"<br/><br/>+ {restantes} actividades más")
                fila.append(Paragraph("".join(partes), celda_estilo))
            data.append(fila)
        alto_disponible = doc.height - 48 * mm
        alto_fila = max(25 * mm, alto_disponible / max(len(semanas), 1))
        tabla = Table(
            data, colWidths=[doc.width / 7] * 7,
            rowHeights=[9 * mm] + [alto_fila] * len(semanas),
        )
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173F32")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#AEBDB5")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 1), (-1, -1), 4),
            ("RIGHTPADDING", (0, 1), (-1, -1), 4),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ]))
        elementos.append(tabla)

    elementos.append(Spacer(1, 3 * mm))
    doc.build(elementos)
    buffer.seek(0)
    return buffer
