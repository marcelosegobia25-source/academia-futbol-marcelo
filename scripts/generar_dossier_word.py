"""Script profesional para generar el Dossier Ejecutivo en formato Word (.docx)
con enfoque 100% en la Nube (SaaS) y capturas de pantalla de alta resolución.
"""

import os
from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

BASE_DIR = Path(__file__).resolve().parent.parent
CAPT_DIR = BASE_DIR / "docs" / "capturas_presentacion"
OUTPUT_DOCX = BASE_DIR / "Dossier_Presentacion_Sistema_Gestion_Academia.docx"
DOCS_COPY = BASE_DIR / "docs" / "Dossier_Presentacion_Sistema_Gestion_Academia.docx"

# Colores del tema ejecutivo
C_NAVY = RGBColor(15, 23, 42)       # #0F172A - Titulares principales
C_EMERALD = RGBColor(5, 150, 105)   # #059669 - Acentos y subtítulos
C_SLATE = RGBColor(51, 65, 85)      # #334155 - Texto base
C_MUTED = RGBColor(100, 116, 139)   # #64748B - Notas y captions
C_WHITE = RGBColor(255, 255, 255)

HEX_NAVY = "0F172A"
HEX_EMERALD = "059669"
HEX_LIGHT_BG = "F8FAFC"
HEX_BORDER = "CBD5E1"
HEX_EMERALD_BG = "ECFDF5"

def set_cell_background(cell, hex_color):
    """Establece color de fondo de una celda."""
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
    """Establece márgenes internos de celda en dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_border_left(cell, hex_color="059669", sz="24"):
    """Agrega borde izquierdo grueso a una celda (estilo callout)."""
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>\n'
        f'  <w:top w:val="none"/>\n'
        f'  <w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{hex_color}"/>\n'
        f'  <w:bottom w:val="none"/>\n'
        f'  <w:right w:val="none"/>\n'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

def add_callout(doc, title, bullet_points, hex_bg=HEX_LIGHT_BG, hex_border=HEX_EMERALD):
    """Crea una caja de texto destacada estilo callout."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.rows[0].cells[0]
    cell.width = Inches(6.5)
    set_cell_background(cell, hex_bg)
    set_cell_border_left(cell, hex_border, sz="28")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=160)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    run_t = p.add_run(f"★  {title.upper()}")
    run_t.font.name = "Calibri"
    run_t.font.size = Pt(10)
    run_t.font.bold = True
    run_t.font.color.rgb = C_EMERALD

    for bp in bullet_points:
        p_bp = cell.add_paragraph()
        p_bp.paragraph_format.space_before = Pt(2)
        p_bp.paragraph_format.space_after = Pt(2)
        run_dot = p_bp.add_run("• ")
        run_dot.font.name = "Calibri"
        run_dot.font.bold = True
        run_dot.font.color.rgb = C_EMERALD
        run_txt = p_bp.add_run(bp)
        run_txt.font.name = "Calibri"
        run_txt.font.size = Pt(9.5)
        run_txt.font.color.rgb = C_SLATE

    # Espacio tras la tabla
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(4)
    p_after.paragraph_format.space_after = Pt(4)

def add_image_box(doc, image_filename, caption_text):
    """Agrega una imagen centrada con marco sutil y pie descriptivo."""
    img_path = CAPT_DIR / image_filename
    if not img_path.exists():
        p_err = doc.add_paragraph(f"[Imagen no encontrada: {image_filename}]")
        p_err.runs[0].font.color.rgb = RGBColor(220, 38, 38)
        return

    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(8)
    p_img.paragraph_format.space_after = Pt(3)
    p_img.paragraph_format.keep_with_next = True
    run = p_img.add_run()
    run.add_picture(str(img_path), width=Inches(6.2))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(2)
    p_cap.paragraph_format.space_after = Pt(12)
    run_cap = p_cap.add_run(f"Figura: {caption_text}")
    run_cap.font.name = "Calibri"
    run_cap.font.size = Pt(8.5)
    run_cap.font.italic = True
    run_cap.font.color.rgb = C_MUTED

def add_feature_table(doc, headers, rows):
    """Crea una tabla elegante con cabecera oscura y filas alternadas."""
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Cabecera
    for i, h_text in enumerate(headers):
        cell = table.cell(0, i)
        set_cell_background(cell, HEX_NAVY)
        set_cell_margins(cell, top=140, bottom=140, left=140, right=140)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(h_text)
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.bold = True
        run.font.color.rgb = C_WHITE

    # Filas de datos
    for r_idx, row_data in enumerate(rows):
        bg = HEX_LIGHT_BG if (r_idx % 2 == 1) else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            cell = table.cell(r_idx + 1, c_idx)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(9)
            run.font.color.rgb = C_SLATE

    # Espacio posterior
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(4)
    p_sp.paragraph_format.space_after = Pt(8)

def construir_documento():
    print("Creando documento Word en la nube (SaaS)...")
    doc = Document()

    # Márgenes de página
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Estilo base
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Calibri'
    style_normal.font.size = Pt(10.5)
    style_normal.font.color.rgb = C_SLATE
    style_normal.paragraph_format.line_spacing = 1.15
    style_normal.paragraph_format.space_after = Pt(6)

    # =========================================================================
    # PORTADA EJECUTIVA CLOUD
    # =========================================================================
    p_tag = doc.add_paragraph()
    p_tag.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tag.paragraph_format.space_before = Pt(36)
    p_tag.paragraph_format.space_after = Pt(6)
    run_tag = p_tag.add_run("PLATAFORMA WEB EN LA NUBE (SaaS) — DOSSIER EJECUTIVO")
    run_tag.font.name = "Calibri"
    run_tag.font.size = Pt(11)
    run_tag.font.bold = True
    run_tag.font.color.rgb = C_EMERALD

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(10)
    run_title = p_title.add_run("SISTEMA INTEGRAL DE GESTIÓN\nPARA ACADEMIAS DEPORTIVAS")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(24)
    run_title.font.bold = True
    run_title.font.color.rgb = C_NAVY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(4)
    p_sub.paragraph_format.space_after = Pt(24)
    run_sub = p_sub.add_run("Solución Cloud Multi-Dispositivo: Control Académico, Deportivo y Financiero 24/7")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(13)
    run_sub.font.color.rgb = C_MUTED

    # Badges Cloud
    t_badges = doc.add_table(rows=1, cols=3)
    t_badges.alignment = WD_TABLE_ALIGNMENT.CENTER
    badges_info = [
        ("☁️ 100% EN LA NUBE", "Acceso 24/7 desde cualquier navegador. Cero instalación local ni servidores."),
        ("📱 MULTI-DISPOSITIVO", "Operatividad simultánea en PC, Laptop, Tablet y Celular desde la cancha u oficina."),
        ("🔒 MÁXIMA SEGURIDAD", "Base de datos Cloud cifrada, protocolo SSL/HTTPS y respaldos automáticos continuos."),
    ]
    for i, (b_title, b_desc) in enumerate(badges_info):
        cell = t_badges.cell(0, i)
        cell.width = Inches(2.15)
        set_cell_background(cell, HEX_LIGHT_BG)
        set_cell_margins(cell, top=140, bottom=140, left=120, right=120)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        r_bt = p.add_run(b_title)
        r_bt.font.name = "Calibri"
        r_bt.font.size = Pt(10)
        r_bt.font.bold = True
        r_bt.font.color.rgb = C_EMERALD

        p_d = cell.add_paragraph()
        p_d.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_d.paragraph_format.space_before = Pt(2)
        p_d.paragraph_format.space_after = Pt(0)
        r_bd = p_d.add_run(b_desc)
        r_bd.font.name = "Calibri"
        r_bd.font.size = Pt(8.5)
        r_bd.font.color.rgb = C_SLATE

    # Metadatos institucionales
    p_meta_sp = doc.add_paragraph()
    p_meta_sp.paragraph_format.space_before = Pt(40)
    p_meta_sp.paragraph_format.space_after = Pt(4)

    t_meta = doc.add_table(rows=4, cols=2)
    t_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_rows = [
        ("Destinatarios:", "Directores de Academia, Coordinadores Deportivos, Tesoreros e Inversionistas"),
        ("Modalidad del Servicio:", "Plataforma Web en la Nube (SaaS - Software as a Service)"),
        ("Disponibilidad y Acceso:", "Acceso Universal 24/7 vía Web desde cualquier dispositivo con navegador"),
        ("Fecha de Publicación:", "Octubre 2026 — Versión Cloud Oficial"),
    ]
    for idx, (label, val) in enumerate(meta_rows):
        cell_lbl = t_meta.cell(idx, 0)
        cell_val = t_meta.cell(idx, 1)
        cell_lbl.width = Inches(2.0)
        cell_val.width = Inches(4.5)
        set_cell_margins(cell_lbl, top=60, bottom=60, left=80, right=80)
        set_cell_margins(cell_val, top=60, bottom=60, left=80, right=80)
        
        p_l = cell_lbl.paragraphs[0]
        p_l.paragraph_format.space_after = Pt(0)
        r_l = p_l.add_run(label)
        r_l.font.bold = True
        r_l.font.size = Pt(9.5)
        r_l.font.color.rgb = C_NAVY

        p_v = cell_val.paragraphs[0]
        p_v.paragraph_format.space_after = Pt(0)
        r_v = p_v.add_run(val)
        r_v.font.size = Pt(9.5)
        r_v.font.color.rgb = C_SLATE

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 1: RESUMEN EJECUTIVO Y PROPUESTA DE VALOR EN LA NUBE
    # =========================================================================
    h1 = doc.add_heading(level=1)
    r = h1.add_run("1. Resumen Ejecutivo y Propuesta de Valor en la Nube")
    r.font.name = "Calibri"
    r.font.size = Pt(17)
    r.font.bold = True
    r.font.color.rgb = C_NAVY

    doc.add_paragraph(
        "El Sistema Integral de Gestión para Academias Deportivas es una moderna plataforma web alojada en la nube (SaaS), "
        "diseñada específicamente para centralizar y profesionalizar toda la operación académica, deportiva, financiera y "
        "administrativa de una institución formativa o competitiva. Al estar 100% en la nube, el sistema elimina las limitaciones "
        "de computadoras físicas fijas, planillas dispersas y cuadernos en papel, permitiendo a todo el equipo trabajar de manera "
        "coordinada y en tiempo real desde cualquier lugar del mundo."
    )

    add_callout(
        doc,
        "VENTAJAS ESTRATÉGICAS DE UNA PLATAFORMA EN LA NUBE (SaaS)",
        [
            "Acceso Inmediato desde Cualquier Lugar: Directores, secretarias y entrenadores acceden desde su computadora, laptop, tablet o teléfono móvil sin importar dónde se encuentren.",
            "Trabajo Colaborativo en Tiempo Real: El profesor registra asistencias en cancha desde su celular, la secretaría cobra mensualidades en recepción y el director supervisa la recaudación desde su hogar simultáneamente.",
            "Cero Instalación y Cero Mantenimiento: No requiere instalar programas ni configurar servidores locales. Se accede de inmediato mediante cualquier navegador moderno (Chrome, Safari, Edge, Firefox).",
            "Cero Riesgo de Pérdida de Información: Sus datos no dependen del disco duro de una computadora que pueda dañarse, extraviarse o infectarse con virus; toda la información está respaldada y protegida en la nube.",
            "Actualizaciones Automáticas y Continuas: Nuevas mejoras y funciones se implementan de forma transparente sin interrumpir las operaciones del club."
        ]
    )

    # Tabla Comparativa de Impacto Cloud
    p_tcomp = doc.add_paragraph()
    r_tcomp = p_tcomp.add_run("Tabla 1: Comparativa Operativa — Gestión Tradicional vs. Plataforma en la Nube")
    r_tcomp.font.bold = True
    r_tcomp.font.color.rgb = C_NAVY

    comp_headers = ["Dimensión Operativa", "Método Tradicional (Excel / Papel / PC Local)", "Plataforma Web en la Nube (SaaS)"]
    comp_rows = [
        ["Acceso y Movilidad", "Atado a una sola computadora en la oficina o a cuadernos físicos.", "Acceso 24/7 desde cualquier dispositivo: PC, tablet o celular en cancha."],
        ["Control de Mensualidades", "Planillas dispersas, olvidos en fechas de corte, morosidad oculta.", "Semáforo automático (Vigente, Por Vencer, Vencido) y recibos oficiales en PDF."],
        ["Concurrencia de Usuarios", "Un solo usuario a la vez; riesgo de sobreescribir archivos compartidos.", "Múltiples usuarios simultáneos con roles y permisos específicos."],
        ["Organización de Torneos", "Cálculo manual de goles, puntos y diferencias propenso a reclamos.", "Fixture automático y tabla de posiciones calculada al instante con cada resultado."],
        ["Seguridad y Respaldo", "Si la computadora de la academia se daña o formatea, se pierden los datos.", "Infraestructura cloud con respaldos automáticos y cifrado SSL de nivel bancario."]
    ]
    add_feature_table(doc, comp_headers, comp_rows)

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 2: INFRAESTRUCTURA CLOUD Y SEGURIDAD DE LA INFORMACIÓN
    # =========================================================================
    h1 = doc.add_heading(level=1)
    r = h1.add_run("2. Infraestructura Cloud, Conectividad y Seguridad")
    r.font.name = "Calibri"
    r.font.size = Pt(17)
    r.font.bold = True
    r.font.color.rgb = C_NAVY

    doc.add_paragraph(
        "La plataforma está desplegada sobre una arquitectura cloud de alta disponibilidad y rendimiento, diseñada para "
        "ofrecer velocidad de respuesta inmediata, soporte concurrente multi-usuario y los más altos estándares de seguridad "
        "en la protección de datos personales y financieros."
    )

    arq_headers = ["Componente Cloud", "Tecnología Implementada", "Beneficio Directo para la Academia"]
    arq_rows = [
        ["Alojamiento Cloud", "Servidores Cloud de Alta Disponibilidad", "Disponibilidad garantizada del 99.9%, accesible los 365 días del año sin caídas."],
        ["Seguridad en Tránsito", "Cifrado SSL / HTTPS de 256 bits", "Toda la información entre su dispositivo y la nube viaja cifrada y protegida contra intrusos."],
        ["Base de Datos Cloud", "Motor Relacional Cloud (PostgreSQL / ACID)", "Consistencia absoluta de datos financieros, sin riesgo de corrupción ni bloqueos."],
        ["Acceso Multi-Dispositivo", "Diseño Web Adaptativo (Responsive Design)", "Se adapta a pantallas de escritorio, notebooks, iPads, tablets Android y smartphones."],
        ["Respaldos Automatizados", "Copias de Seguridad Diarias en la Nube", "Respaldos automáticos continuos más la opción de descargar un backup completo en ZIP en cualquier momento."]
    ]
    add_feature_table(doc, arq_headers, arq_rows)

    add_callout(
        doc,
        "SEGURIDAD Y PRIVACIDAD DE DATOS DE MENORES Y TUTORES",
        [
            "Aislamiento de Información: Los datos de su academia son estrictamente privados y confidenciales.",
            "Cumplimiento de Seguridad: Cuentas individuales protegidas con contraseñas seguras y bloqueo automático ante intentos no autorizados.",
            "Trazabilidad Integral: Cada acción (quién cobró una cuota, quién modificó una ficha o quién registró un marcador) queda asentada con fecha, hora y usuario."
        ],
        hex_bg=HEX_EMERALD_BG,
        hex_border=HEX_EMERALD
    )

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 3: RECORRIDO VISUAL PANTALLA A PANTALLA (SHOWCASE CLOUD)
    # =========================================================================
    h1 = doc.add_heading(level=1)
    r = h1.add_run("3. Demostración Visual Pantalla a Pantalla de Cada Módulo")
    r.font.name = "Calibri"
    r.font.size = Pt(17)
    r.font.bold = True
    r.font.color.rgb = C_NAVY

    doc.add_paragraph(
        "A continuación se presenta un recorrido visual completo por todas las funciones de la plataforma web en la nube, "
        "con capturas reales del sistema en funcionamiento. Cada pantalla refleja la interfaz moderna, oscura y profesional "
        "diseñada para una experiencia de usuario rápida, fluida e intuitiva."
    )

    # 3.1
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.1 Centro de Comando y Acceso Seguro a la Nube")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "La puerta de acceso a la plataforma web. Cada miembro del equipo ingresa con sus credenciales individuales. "
        "El sistema cuenta con blindaje activo contra intentos de intrusión que bloquea temporalmente el acceso tras 5 intentos fallidos."
    )
    add_image_box(doc, "01_login.png", "Pantalla de inicio de sesión web con validación de credenciales, logotipo del club y blindaje de seguridad.")

    add_callout(
        doc,
        "PUNTOS DESTACADOS DEL ACCESO",
        [
            "Ingreso limpio y directo sin textos precargados, con foco activo inmediato para ingresar usuario y clave.",
            "Protección contra ataques de fuerza bruta y bloqueo automático de direcciones sospechosas.",
            "Sesiones seguras con control de inactividad para proteger la privacidad en equipos compartidos."
        ]
    )

    # 3.2
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.2 Panel de Control Ejecutivo (Dashboard en Tiempo Real)")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "El centro de mando directivo. Al ingresar, el sistema despliega de forma visual e instantánea el estado general "
        "de la institución: jugadores activos, mensualidades al día versus alumnos morosos, recaudación total del mes y accesos directos."
    )
    add_image_box(doc, "02_dashboard_principal.png", "Dashboard ejecutivo en tiempo real con indicadores clave (KPIs), resumen financiero y accesos directos.")

    add_callout(
        doc,
        "MÉTRICAS CLAVE DISPONIBLES AL INSTANTE",
        [
            "Padrón Activo vs. Bajas: Monitoreo permanente de la matrícula institucional.",
            "Semáforo de Pagos: Detección inmediata de alumnos en mora para agilizar la gestión de cobranza.",
            "Recaudación Mensual Consolidada: Monto acumulado y cantidad de cuotas ingresadas en el periodo.",
            "Descarga de Respaldos Completos en 1 Clic para archivar copias locales cuando la dirección lo desee."
        ]
    )

    doc.add_page_break()

    # 3.3
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.3 Padrón Integral de Alumnos y Ficha del Deportista")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "Permite gestionar el historial completo de cada deportista. Cuenta con filtros inteligentes por categoría, estado "
        "(Activo / Retirado) y búsqueda rápida por nombre o carnet de identidad."
    )
    add_image_box(doc, "03_alumnos_listado.png", "Directorio web de alumnos con filtros dinámicos por categoría, estado deportivo y buscador en vivo.")

    doc.add_paragraph(
        "El formulario de inscripción digital captura la información personal, datos médicos, tutores responsables y "
        "calcula automáticamente la categoría correspondiente según la fecha de nacimiento."
    )
    add_image_box(doc, "04_alumnos_nuevo.png", "Formulario digital de inscripción de deportista con categorización automática por edad.")

    doc.add_paragraph(
        "La Ficha Técnica Individual consolida el perfil físico (estatura, peso, pierna hábil, posición táctica), "
        "el historial de los últimos 6 pagos y permite generar con un clic la Ficha Oficial en PDF con foto."
    )
    add_image_box(doc, "05_alumnos_ficha.png", "Ficha técnica integral del deportista con datos de tutores, características físicas y exportación a PDF.")

    add_callout(
        doc,
        "BENEFICIOS DE LA FICHA DIGITAL",
        [
            "Categorización Automática: Elimina errores de inscripción de niños en categorías no correspondientes.",
            "Ficha PDF Imprimible y Compartible: Perfecta para enviar por WhatsApp o correo a padres y ligas deportivas.",
            "Trazabilidad Financiera Integrada: El cuerpo técnico o secretaría visualiza el estado de cuotas dentro del mismo perfil."
        ]
    )

    doc.add_page_break()

    # 3.4
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.4 Control Financiero, Cobranza de Cuotas y Recibos Oficiales")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "El módulo financiero resuelve las pérdidas por cuotas olvidadas. Opera con un algoritmo inteligente de continuidad de "
        "mensualidades que calcula el próximo vencimiento a partir de la fecha base del primer pago, asegurando que no queden meses impagos."
    )
    add_image_box(doc, "06_pagos_control.png", "Módulo de mensualidades con semáforo preventivo de vencimientos y filtros por periodo.")

    doc.add_paragraph(
        "Al registrar un cobro, el sistema valida la tarifa base de la academia, aplica becas si corresponde y genera al instante "
        "un recibo formal en PDF con numeración correlativa y logotipo del club para enviar digitalmente a los tutores."
    )
    add_image_box(doc, "07_pagos_nuevo.png", "Registro de cobro de mensualidad con cálculo automático, método de pago y emisión de recibo en PDF.")

    add_callout(
        doc,
        "VENTAJAS DE LA GESTIÓN DE COBRANZAS EN LA NUBE",
        [
            "Semáforo Inteligente: Alerta preventiva de cuotas por vencer (5 días antes) y cuotas vencidas.",
            "Imposibilidad de Doble Cobro: Validación a nivel de base de datos que impide cobrar dos veces el mismo mes por error.",
            "Exportación Contable: Descarga de historiales completos a Excel (.xlsx) y balances en PDF para auditoría interna.",
            "Recibos Digitales en PDF: Reducción del gasto en talonarios de papel y mayor transparencia hacia las familias."
        ]
    )

    doc.add_page_break()

    # 3.5
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.5 Organización de Campeonatos, Fixtures Automáticos y Posiciones")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "Organizar torneos internos o ligas competitivas es simple y automático. El sistema genera el rol de partidos "
        "(todos contra todos o fases de eliminación directa) y recalcula la tabla de posiciones en tiempo real al ingresar los goles."
    )
    add_image_box(doc, "08_campeonatos_listado.png", "Directorio de campeonatos y torneos con estado y avance de fechas disputadas.")

    doc.add_paragraph(
        "En la vista detallada del campeonato, la Tabla de Posiciones (PJ, PG, PE, PP, GF, GC, DG y Puntos) se actualiza "
        "inmediatamente tras guardar el resultado de cada jornada."
    )
    add_image_box(doc, "09_campeonato_detalle.png", "Detalle de torneo con fixture por jornadas, marcadores en vivo y tabla de posiciones recalculada al instante.")

    doc.add_paragraph(
        "Incluye control de habilitación y fichaje de jugadores por torneo, evitando la inclusión de deportistas que no cumplan "
        "con la categoría o documentación requerida."
    )
    add_image_box(doc, "10_campeonato_jugadores.png", "Panel de habilitación de jugadores participantes en el torneo.")

    doc.add_paragraph(
        "Además, gestiona el Directorio de Clubes Rivales con datos de contacto, sedes y colores representativos."
    )
    add_image_box(doc, "11_campeonatos_rivales.png", "Directorio de clubes rivales y academias invitadas a campeonatos.")

    add_callout(
        doc,
        "POTENCIA DE LA GESTIÓN COMPETITIVA",
        [
            "Generación Instantánea de Fixture: Crea calendarios equilibrados de local y visitante con un solo clic.",
            "Recálculo Matemático Seguro: Si se rectifica un marcador, toda la tabla de posiciones se reconstruye automáticamente sin margen de error.",
            "Reglamentación de Walkovers (W.O.): Asignación reglamentaria de victoria 3-0 y puntos directos.",
            "Exportación a PDF y Excel: Tablas y roles listos para imprimir o compartir en redes sociales de la academia."
        ]
    )

    doc.add_page_break()

    # 3.6
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.6 Programación de Partidos y Planillas de Convocatoria")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "El cuerpo técnico programa encuentros oficiales y amistosos, asignando categoría, rival, cancha y horario. "
        "Cada partido genera automáticamente la Planilla Oficial de Convocatoria en PDF para el día del juego."
    )
    add_image_box(doc, "12_partidos_programacion.png", "Listado de partidos programados con enlace directo a generación de planilla de convocatoria en PDF.")

    add_callout(
        doc,
        "BENEFICIOS OPERATIVOS EN DÍA DE PARTIDO",
        [
            "Sincronización Automática con la Agenda: Todos los partidos se reflejan en el calendario general del club.",
            "Planilla de Convocatoria Lista para Cancha: Formato oficial con nombres, dorsales y espacio para firmas de planillaje.",
            "Gestión de Sedes: Asignación clara del complejo deportivo donde se disputará el encuentro."
        ]
    )

    # 3.7
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.7 Agenda Cloud, Calendario Interactivo y Entrenamientos")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "Visibilidad 360° de toda la actividad deportiva e institucional. Combina una Agenda cronológica, un Calendario visual "
        "mensual/semanal y un planificador de horarios de entrenamiento fijos."
    )
    add_image_box(doc, "13_agenda_eventos.png", "Agenda de eventos, partidos y compromisos institucionales de la academia.")

    doc.add_paragraph(
        "El Calendario Mensual consolida partidos, entrenamientos de todas las categorías y reuniones, permitiendo exportar "
        "la programación en formato PDF para los padres de familia."
    )
    add_image_box(doc, "14_calendario_mensual.png", "Calendario interactivo mensual que unifica entrenamientos, partidos y eventos especiales.")

    doc.add_paragraph(
        "Los entrenamientos recurrentes se configuran por día, hora, categoría y profesor a cargo, evitando colisiones de uso en las canchas."
    )
    add_image_box(doc, "15_calendario_entrenamientos.png", "Configuración de entrenamientos semanales fijos por categoría, cancha y horario.")

    doc.add_page_break()

    # 3.8
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.8 Control de Asistencia en Cancha y Cuerpo Técnico")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "Diseñado para que los profesores tomen asistencia directamente desde su teléfono o tablet al borde de la cancha. "
        "Permite registrar presentes, ausencias y justificaciones, calculando porcentajes de presentismo automáticamente."
    )
    add_image_box(doc, "16_asistencia_entrenamiento.png", "Planilla interactiva de asistencia a entrenamientos adaptada a dispositivos móviles en cancha.")

    doc.add_paragraph(
        "El módulo de Cuerpo Técnico centraliza la nómina de entrenadores, preparadores físicos y coordinadores deportivos."
    )
    add_image_box(doc, "17_personal_deportivo.png", "Directorio del cuerpo técnico y entrenadores de la academia.")

    # 3.9
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.9 Estructura Deportiva: Categorías, Equipos y Sedes")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "Configuración flexible de categorías según las edades de los alumnos (Sub-7, Sub-9, Sub-11, Sub-13, hasta categorías mayores)."
    )
    add_image_box(doc, "18_categorias.png", "Configuración de rangos de edad por categoría formativa.")

    doc.add_paragraph(
        "Los equipos pueden configurarse de forma global o por categoría específica, permitiendo proyectar planteles competitivos (A, B, C)."
    )
    add_image_box(doc, "19_equipos.png", "Administración de equipos globales y filiales por categoría.")

    doc.add_paragraph(
        "En Sedes y Lugares se registran los complejos deportivos donde opera la institución, especificando el tipo de superficie."
    )
    add_image_box(doc, "20_lugares_sedes.png", "Directorio de sedes deportivas y canchas de entrenamiento.")

    doc.add_page_break()

    # 3.10
    h2 = doc.add_heading(level=2)
    r = h2.add_run("3.10 Seguridad de Usuarios, Bitácora de Auditoría y Configuración")
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_EMERALD

    doc.add_paragraph(
        "Administración granular de roles: cree cuentas para Secretaría (cobros e inscripciones), Profesores (asistencias y partidos) "
        "o Directores (acceso total), resguardando los datos sensibles de la institución."
    )
    add_image_box(doc, "21_usuarios_roles.png", "Panel de administración de usuarios, asignación de roles y matriz de permisos de seguridad.")

    doc.add_paragraph(
        "Cada movimiento en la nube queda auditado con fecha, hora, usuario interviniente y dirección IP, garantizando total transparencia."
    )
    add_image_box(doc, "22_auditoria_sistema.png", "Módulo de auditoría integral y trazabilidad con registro cronológico de todas las operaciones.")

    doc.add_paragraph(
        "Personalice la identidad institucional: suba el logotipo del club (visible en todos los recibos y fichas PDF), defina la "
        "moneda de cobro y la cuota mensual estándar."
    )
    add_image_box(doc, "23_configuracion_academia.png", "Panel de personalización institucional para carga de logotipo, monto de cuota y respaldos.")

    add_callout(
        doc,
        "RESPALDOS AUTOMÁTICOS EN LA NUBE Y EXPORTABILIDAD",
        [
            "Respaldos Cloud Gestionados: La base de datos se respalda automáticamente de forma diaria sin intervención manual.",
            "Exportación Transportable: Desde la pantalla de configuración, la dirección puede generar un archivo .ZIP completo con la base, fotos y documentos con un solo clic.",
            "Propiedad Total: La academia conserva la titularidad y control absoluto de su información en todo momento."
        ],
        hex_bg=HEX_LIGHT_BG,
        hex_border=HEX_EMERALD
    )

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 4: VENTAJAS DEL MODELO SAAS (SIN REQUISITOS DE HARDWARE)
    # =========================================================================
    h1 = doc.add_heading(level=1)
    r = h1.add_run("4. Ventajas del Modelo en la Nube frente a Sistemas Tradicionales")
    r.font.name = "Calibri"
    r.font.size = Pt(17)
    r.font.bold = True
    r.font.color.rgb = C_NAVY

    doc.add_paragraph(
        "Al tratarse de una solución moderna 100% web alojada en la nube, la academia NO necesita invertir en servidores costosos, "
        "ni preocuparse por especificaciones técnicas complejas de procesadores o memorias en computadoras locales. "
        "Cualquier dispositivo con un navegador web y conexión a internet tiene acceso pleno e inmediato a la plataforma."
    )

    cloud_headers = ["Aspecto Tecnológico", "Sistemas Tradicionales de Escritorio", "Nuestra Solución Web en la Nube (SaaS)"]
    cloud_rows = [
        ["Requisitos de Hardware", "Exigen computadoras potentes, memoria RAM dedicada y espacio en disco.", "CERO requisitos especiales: funciona en cualquier PC, laptop, tablet o smartphone."],
        ["Instalación y Configuración", "Instalación compleja por computadora, licencias por equipo, instaladores .exe.", "CERO instalación: se abre el navegador (Chrome, Safari, Edge) y se ingresa."],
        ["Compatibilidad de Sistema", "Limitado generalmente a versiones específicas de Windows.", "100% universal: compatible con Windows, Mac (macOS), Android, iOS (iPhone/iPad) y Linux."],
        ["Riesgo de Pérdida de Datos", "Si la computadora se quema, es robada o se formatea, se pierde todo.", "Datos 100% seguros y respaldados continuamente en la nube."],
        ["Mantenimiento y Soporte", "Requiere contratar técnicos para parches, formateos y copias de seguridad.", "Mantenimiento, copias de seguridad y mejoras técnicas 100% gestionadas en la nube."],
        ["Puesta en Marcha (Onboarding)", "Días o semanas de instalación y configuración en cada computadora.", "Habilitación inmediata: su academia puede estar operando en minutos."]
    ]
    add_feature_table(doc, cloud_headers, cloud_rows)

    add_callout(
        doc,
        "ACCESO INSTANTÁNEO MULTI-DISPOSITIVO",
        [
            "En la Recepción / Oficina: Computadora o notebook de secretaría para cobro de cuotas, emisión de recibos e inscripciones.",
            "En el Campo de Juego / Cancha: Tablet o smartphone del profesor para verificar fichas médicas y registrar asistencias en vivo.",
            "En Casa o de Viaje: Celular o laptop de la directiva para revisar la recaudación y tomar decisiones estratégicas en tiempo real."
        ]
    )

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 5: BENEFICIOS ECONÓMICOS, RETORNO DE INVERSIÓN (ROI) Y CONTACTO
    # =========================================================================
    h1 = doc.add_heading(level=1)
    r = h1.add_run("5. Beneficios para la Academia y Retorno de Inversión (ROI)")
    r.font.name = "Calibri"
    r.font.size = Pt(17)
    r.font.bold = True
    r.font.color.rgb = C_NAVY

    doc.add_paragraph(
        "Adoptar la plataforma web genera un retorno financiero y operativo inmediato para la academia, impactando directamente "
        "en la recaudación mensual y en la satisfacción de las familias:"
    )

    roi_headers = ["Dimensión de Impacto", "Beneficio Cuantificable", "Resultado Práctico para la Institución"]
    roi_rows = [
        ["Recuperación de Morosidad", "Aumento del 25% al 35% en cobros puntuales", "El semáforo preventivo y el control continuo evitan que alumnos acumulen meses sin pagar."],
        ["Ahorro en Horas Hombre", "Más de 15 horas semanales ahorradas", "Elimina el llenado de recibos manuales, el armado de tablas en Excel y llamadas de reclamo."],
        ["Ahorro en Papelería y Talonarios", "Reducción del 90% en costos de impresión", "Emisión digital de recibos de pago en PDF, fichas técnicas y convocatorias deportivas."],
        ["Prestigio y Retención de Alumnos", "Mayor confianza de los padres de familia", "Comprobantes digitales formales, control disciplinario y organización profesional reducen la deserción."]
    ]
    add_feature_table(doc, roi_headers, roi_rows)

    add_callout(
        doc,
        "DISPONIBILIDAD Y PUESTA EN MARCHA INMEDIATA",
        [
            "La plataforma se encuentra actualmente en producción y completamente operativa en la nube.",
            "Ofrecemos demostración guiada en vivo para directores, coordinadores y personal administrativo.",
            "Contáctenos para habilitar su academia en la nube y comenzar la digitalización integral de su institución."
        ],
        hex_bg=HEX_EMERALD_BG,
        hex_border=HEX_EMERALD
    )

    p_fin = doc.add_paragraph()
    p_fin.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fin.paragraph_format.space_before = Pt(30)
    r_fin = p_fin.add_run("— FIN DEL DOSSIER DE PRESENTACIÓN —\nSistema Integral de Gestión para Academias Deportivas (Plataforma Web en la Nube)")
    r_fin.font.name = "Calibri"
    r_fin.font.size = Pt(10)
    r_fin.font.italic = True
    r_fin.font.color.rgb = C_MUTED

    # Guardar en las distintas ubicaciones
    archivos_salida = [
        OUTPUT_DOCX,
        DOCS_COPY,
        BASE_DIR / "Dossier_Presentacion_Sistema_Gestion_Academia_Nube.docx",
        BASE_DIR / "Dossier_Presentacion_Sistema_Gestion_Academia_Actualizado.docx",
    ]
    for ruta in archivos_salida:
        try:
            doc.save(str(ruta))
            print(f"Guardado exitosamente en: {ruta}")
        except PermissionError:
            print(f"Aviso: {ruta.name} está abierto en Word (bloqueado). Se omitió sobreescritura.")

    print("¡Proceso de generación completado con éxito!")

if __name__ == "__main__":
    construir_documento()
