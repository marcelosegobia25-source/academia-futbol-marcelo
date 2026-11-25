"""Generador de la Ficha Comercial Ejecutiva de 1 SOLA HOJA (One-Pager).

Diseñado específicamente para presentaciones ejecutivas, reuniones comerciales y entrega a directores:
- Formato ultra-compacto y de alto impacto visual.
- Exactamente 1 sola página (márgenes optimizados, 2 columnas, tipografía ejecutiva).
- 100% actualizado al modelo Cloud actual (SaaS, PostgreSQL en Supabase, Render, WhatsApp 71054702).
- Elimina módulos obsoletos (caja antigua, instaladores locales .exe, inventario/ventas desfasado).
- Logotipo oficial e identidad corporativa de include SOFTWARE STUDIO.
"""

from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DOCX_ROOT = BASE_DIR / "Ficha_Comercial_Sistema_Gestion_Academias.docx"
OUTPUT_DOCX_DOCS = BASE_DIR / "docs" / "Ficha_Comercial_Sistema_Gestion_Academias.docx"
LOGO_PATH = BASE_DIR / "docs" / "brand" / "logo_include_2x.png"

# Paleta ejecutiva
C_NAVY = RGBColor(15, 23, 42)       # #0F172A
C_EMERALD = RGBColor(5, 150, 105)   # #059669
C_SLATE = RGBColor(51, 65, 85)      # #334155
C_MUTED = RGBColor(100, 116, 139)   # #64748B
C_WHITE = RGBColor(255, 255, 255)

HEX_NAVY = "0F172A"
HEX_EMERALD = "059669"
HEX_LIGHT_BG = "F8FAFC"
HEX_BORDER = "E2E8F0"
HEX_EMERALD_BG = "ECFDF5"
HEX_EMERALD_LIGHT = "D1FAE5"

def set_cell_background(cell, hex_color):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def set_cell_margins(cell, top=60, bottom=60, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_border(cell, top="none", bottom="none", left="none", right="none", color=HEX_BORDER, sz="8"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>\n'
        f'  <w:top w:val="{top}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:left w:val="{left}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:bottom w:val="{bottom}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:right w:val="{right}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

def generar_ficha_1_hoja():
    doc = Document()

    # 1. Configuración de página: Márgenes estrechos (0.4 pulgadas) para encajar 1 hoja perfecta
    for section in doc.sections:
        section.top_margin = Inches(0.38)
        section.bottom_margin = Inches(0.38)
        section.left_margin = Inches(0.45)
        section.right_margin = Inches(0.45)
        section.header_distance = Inches(0.15)
        section.footer_distance = Inches(0.15)

    # =========================================================================
    # ENCABEZADO SUPERIOR: Logo Proveedor + Badges Cloud de Alto Impacto
    # =========================================================================
    t_header = doc.add_table(rows=1, cols=2)
    t_header.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_header.autofit = False

    cell_logo = t_header.rows[0].cells[0]
    cell_badge = t_header.rows[0].cells[1]
    cell_logo.width = Inches(3.2)
    cell_badge.width = Inches(4.4)
    set_cell_margins(cell_logo, top=0, bottom=40, left=0, right=60)
    set_cell_margins(cell_badge, top=0, bottom=40, left=60, right=0)

    # Logo
    p_logo = cell_logo.paragraphs[0]
    p_logo.paragraph_format.space_before = Pt(0)
    p_logo.paragraph_format.space_after = Pt(2)
    if LOGO_PATH.exists():
        r_img = p_logo.add_run()
        r_img.add_picture(str(LOGO_PATH), width=Inches(1.85))
    else:
        r_txt = p_logo.add_run("include SOFTWARE STUDIO")
        r_txt.font.bold = True
        r_txt.font.size = Pt(13)
        r_txt.font.color.rgb = C_NAVY

    p_dev = cell_logo.add_paragraph()
    p_dev.paragraph_format.space_before = Pt(0)
    p_dev.paragraph_format.space_after = Pt(0)
    r_dev = p_dev.add_run("Estudio de Ingeniería de Software • Soluciones Cloud")
    r_dev.font.size = Pt(7.5)
    r_dev.font.color.rgb = C_MUTED

    # Badges derecha
    p_b = cell_badge.paragraphs[0]
    p_b.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_b.paragraph_format.space_before = Pt(2)
    p_b.paragraph_format.space_after = Pt(0)
    
    r_b1 = p_b.add_run("☁️ CLOUD SAAS 24/7   |   📱 MULTI-DISPOSITIVO   |   💬 WHATSAPP DIRECTO")
    r_b1.font.name = "Calibri"
    r_b1.font.bold = True
    r_b1.font.size = Pt(8)
    r_b1.font.color.rgb = C_EMERALD

    p_b2 = cell_badge.add_paragraph()
    p_b2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_b2.paragraph_format.space_before = Pt(1)
    p_b2.paragraph_format.space_after = Pt(0)
    r_b2 = p_b2.add_run("Producción Activa: academia-futbol-marcelo.onrender.com")
    r_b2.font.size = Pt(8)
    r_b2.font.bold = True
    r_b2.font.color.rgb = C_NAVY

    # =========================================================================
    # BANNER DE TÍTULO PRINCIPAL Y PROPUESTA DE VALOR
    # =========================================================================
    p_sep = doc.add_paragraph()
    p_sep.paragraph_format.space_before = Pt(3)
    p_sep.paragraph_format.space_after = Pt(1)

    t_title = doc.add_table(rows=1, cols=1)
    t_title.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_title.autofit = False
    c_title = t_title.rows[0].cells[0]
    c_title.width = Inches(7.6)
    set_cell_background(c_title, HEX_LIGHT_BG)
    set_cell_border(c_title, top="single", bottom="single", left="single", right="single", color=HEX_BORDER, sz="8")
    set_cell_margins(c_title, top=80, bottom=80, left=140, right=140)

    p_t = c_title.paragraphs[0]
    p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_t.paragraph_format.space_before = Pt(0)
    p_t.paragraph_format.space_after = Pt(2)
    r_t = p_t.add_run("PLATAFORMA INTEGRAL DE GESTIÓN PARA ACADEMIAS DEPORTIVAS")
    r_t.font.name = "Calibri"
    r_t.font.size = Pt(13.5)
    r_t.font.bold = True
    r_t.font.color.rgb = C_NAVY

    p_sub = c_title.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(0)
    r_sub = p_sub.add_run("Digitalización deportiva en la nube, control de mensualidades sin fugas y captación web en tiempo real")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(9)
    r_sub.font.color.rgb = C_EMERALD
    r_sub.font.bold = True

    # Espacio previo a las columnas
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(3)
    p_sp.paragraph_format.space_after = Pt(0)

    # =========================================================================
    # CUERPO PRINCIPAL: MATRIZ DE 2 COLUMNAS (6 MÓDULOS DE VALOR)
    # =========================================================================
    t_body = doc.add_table(rows=3, cols=2)
    t_body.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_body.autofit = False

    modulos = [
        # Fila 1 - Columna 1
        (0, 0, "1. CAPTACIÓN WEB & WHATSAPP (LANDING PAGE)", [
            ("Sitio Web Oficial:", "Diseño atlético de alto impacto, 100% responsive para celulares."),
            ("Conversión Rápida:", "Exhibición de categorías, horarios, metodología y canchas."),
            ("WhatsApp Directo (+591 71054702):", "Botón flotante para cerrar inscripciones en 1 clic."),
        ], HEX_LIGHT_BG),

        # Fila 1 - Columna 2
        (0, 1, "2. CONTROL FINANCIERO Y CERO FUGAS (MOTOR DE COBRO)", [
            ("Semáforo Inteligente:", "Al día, Abono parcial y Vencido (deudor real) en tiempo real."),
            ("Becas Completas (100%):", "Excluidas de deuda para evitar reclamos y falsos morosos."),
            ("Recibos Oficiales en PDF:", "Comprobante numerado con envío directo al WhatsApp del tutor."),
        ], HEX_EMERALD_BG),

        # Fila 2 - Columna 1
        (1, 0, "3. GESTIÓN ACADÉMICA Y FICHA DEL ALUMNO", [
            ("Ficha Técnica Completa:", "C.I., fecha de nacimiento, tutor, teléfono y datos de salud."),
            ("Cálculo Automático de Categoría:", "Previene descalificaciones en torneos por mala edad."),
            ("Ficha Oficial PDF:", "Credencial formal con fotografía lista para imprimir o compartir."),
        ], HEX_LIGHT_BG),

        # Fila 2 - Columna 2
        (1, 1, "4. CONTROL DEPORTIVO EN CANCHA (MOBILE-FIRST)", [
            ("Asistencias en 30 Segundos:", "El profesor pasa lista desde su celular en la cancha."),
            ("Convocatorias y Partidos:", "Generación de nómina de convocados y exportación en PDF."),
            ("Torneos y Fixture:", "Seguimiento de rivales, resultados y tablas de posiciones."),
        ], HEX_LIGHT_BG),

        # Fila 3 - Columna 1
        (2, 0, "5. SEGURIDAD, AUDITORÍA Y DISPONIBILIDAD 24/7", [
            ("100% en la Nube (SaaS):", "Sin instalaciones en computadoras ni riesgo de virus locales."),
            ("PostgreSQL Cloud (Supabase):", "Base de datos relacional con conexiones cifradas SSL."),
            ("Auditoría Interna Inmutable:", "Registro de quién cobró, quién editó, IP y fecha exacta."),
        ], HEX_LIGHT_BG),

        # Fila 3 - Columna 2
        (2, 1, "6. RETORNO DE INVERSIÓN Y BENEFICIOS INMEDIATOS", [
            ("+35% en Cobranza Puntual:", "Recordatorios por WhatsApp eliminan olvidos de mensualidad."),
            ("15+ Horas Semanales Ahorradas:", "Cero cuadernos, cero llamadas y cero planillas dispersas."),
            ("Imagen Profesional de Élite:", "Comprobantes digitales y credenciales que fidelizan a los padres."),
        ], HEX_EMERALD_BG),
    ]

    for r_idx, c_idx, title, items, bg_color in modulos:
        cell = t_body.rows[r_idx].cells[c_idx]
        cell.width = Inches(3.72)
        set_cell_background(cell, bg_color)
        set_cell_border(cell, top="single", bottom="single", left="single", right="single", color=HEX_BORDER, sz="6")
        set_cell_margins(cell, top=50, bottom=50, left=80, right=80)

        p_mod_title = cell.paragraphs[0]
        p_mod_title.paragraph_format.space_before = Pt(0)
        p_mod_title.paragraph_format.space_after = Pt(2)
        r_mt = p_mod_title.add_run(title)
        r_mt.font.name = "Calibri"
        r_mt.font.size = Pt(8.5)
        r_mt.font.bold = True
        r_mt.font.color.rgb = C_NAVY if bg_color == HEX_LIGHT_BG else C_EMERALD

        for label, desc in items:
            p_it = cell.add_paragraph()
            p_it.paragraph_format.space_before = Pt(1)
            p_it.paragraph_format.space_after = Pt(1)
            r_dot = p_it.add_run("▪ ")
            r_dot.font.name = "Calibri"
            r_dot.font.size = Pt(7.5)
            r_dot.font.bold = True
            r_dot.font.color.rgb = C_EMERALD

            r_lbl = p_it.add_run(f"{label} ")
            r_lbl.font.name = "Calibri"
            r_lbl.font.size = Pt(7.8)
            r_lbl.font.bold = True
            r_lbl.font.color.rgb = C_SLATE

            r_desc = p_it.add_run(desc)
            r_desc.font.name = "Calibri"
            r_desc.font.size = Pt(7.8)
            r_desc.font.color.rgb = C_SLATE

    # =========================================================================
    # FOOTER BAR INFERIOR: Contacto, Demo en Vivo y Respaldo Empresarial
    # =========================================================================
    p_sp_foot = doc.add_paragraph()
    p_sp_foot.paragraph_format.space_before = Pt(4)
    p_sp_foot.paragraph_format.space_after = Pt(0)

    t_foot = doc.add_table(rows=1, cols=1)
    t_foot.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_foot.autofit = False
    c_foot = t_foot.rows[0].cells[0]
    c_foot.width = Inches(7.6)
    set_cell_background(c_foot, HEX_NAVY)
    set_cell_margins(c_foot, top=60, bottom=60, left=100, right=100)

    p_f1 = c_foot.paragraphs[0]
    p_f1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_f1.paragraph_format.space_before = Pt(0)
    p_f1.paragraph_format.space_after = Pt(1)
    r_f1 = p_f1.add_run("DEMO EN VIVO Y PUESTA EN MARCHA INMEDIATA (24 HORAS)")
    r_f1.font.name = "Calibri"
    r_f1.font.bold = True
    r_f1.font.size = Pt(9)
    r_f1.font.color.rgb = C_WHITE

    p_f2 = c_foot.add_paragraph()
    p_f2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_f2.paragraph_format.space_before = Pt(0)
    p_f2.paragraph_format.space_after = Pt(0)

    r_f2_1 = p_f2.add_run("🌐 Plataforma: ")
    r_f2_1.font.size = Pt(8)
    r_f2_1.font.color.rgb = RGBColor(148, 163, 184)
    r_f2_2 = p_f2.add_run("https://academia-futbol-marcelo.onrender.com   ")
    r_f2_2.font.size = Pt(8)
    r_f2_2.font.bold = True
    r_f2_2.font.color.rgb = RGBColor(52, 211, 153)

    r_f2_3 = p_f2.add_run("|   📱 WhatsApp Comercial: ")
    r_f2_3.font.size = Pt(8)
    r_f2_3.font.color.rgb = RGBColor(148, 163, 184)
    r_f2_4 = p_f2.add_run("+591 71054702   ")
    r_f2_4.font.size = Pt(8)
    r_f2_4.font.bold = True
    r_f2_4.font.color.rgb = C_WHITE

    r_f2_5 = p_f2.add_run("|   ⚡ include SOFTWARE STUDIO")
    r_f2_5.font.size = Pt(8)
    r_f2_5.font.bold = True
    r_f2_5.font.color.rgb = RGBColor(56, 189, 248)

    # Guardar en las distintas ubicaciones
    archivos_salida = [
        BASE_DIR / "Ficha_Comercial_Sistema_Gestion_Academias_1_Hoja.docx",
        OUTPUT_DOCX_DOCS,
        BASE_DIR / "docs" / "Ficha_Comercial_Sistema_Gestion_Academias_1_Hoja.docx",
        OUTPUT_DOCX_ROOT,
    ]
    for ruta in archivos_salida:
        try:
            doc.save(str(ruta))
            print(f"Guardado exitosamente en: {ruta.name}")
        except PermissionError:
            print(f"Aviso: {ruta.name} está abierto en Word. Se generó como {archivos_salida[0].name}.")

    print("Ficha comercial de 1 SOLA HOJA completada con éxito.")

if __name__ == "__main__":
    generar_ficha_1_hoja()
