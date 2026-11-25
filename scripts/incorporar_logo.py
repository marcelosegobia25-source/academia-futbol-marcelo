"""Script para incorporar el logotipo oficial y la identidad corporativa de
'include SOFTWARE STUDIO' en toda la documentación ejecutiva y comercial.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

logo_docs = """<p align="center">
  <img src="brand/logo_include_transparent.png" alt="include SOFTWARE STUDIO" width="280">
</p>

"""

logo_root = """<p align="center">
  <img src="docs/brand/logo_include_transparent.png" alt="include SOFTWARE STUDIO" width="280">
</p>

"""

def procesar():
    # 1. docs/PRESENTACION_RESUMEN_10_HOJAS.md
    p1 = BASE_DIR / "docs" / "PRESENTACION_RESUMEN_10_HOJAS.md"
    if p1.exists():
        c = p1.read_text(encoding="utf-8")
        if "logo_include" not in c:
            c = logo_docs + c
            c = c.replace("**Versión:** 1.0.0", "**Desarrollo & Tecnología:** include SOFTWARE STUDIO  \n**Versión:** 1.3.0 Cloud")
            footer = "\n\n---\n\n<p align=\"center\">\n  <b>include SOFTWARE STUDIO</b> — <i>Soluciones Tecnológicas de Alto Impacto</i><br>\n  Todos los derechos reservados © 2026\n</p>\n"
            c = c + footer
            p1.write_text(c, encoding="utf-8")
            print("Actualizado:", p1.name)

    # 2. docs/RESUMEN_CLIENTE_2_HOJAS.md
    p2 = BASE_DIR / "docs" / "RESUMEN_CLIENTE_2_HOJAS.md"
    if p2.exists():
        c = p2.read_text(encoding="utf-8")
        if "logo_include" not in c:
            c = logo_docs + c.replace(
                "## Academia Deportiva - Solución Integral de Gestión",
                "## Academia Deportiva - Solución Integral de Gestión\n**Desarrollado y Provisto por:** include SOFTWARE STUDIO"
            )
            p2.write_text(c, encoding="utf-8")
            print("Actualizado:", p2.name)

    # 3. docs/PROPUESTA_COMERCIAL_Y_MARCO_LEGAL.md
    p3 = BASE_DIR / "docs" / "PROPUESTA_COMERCIAL_Y_MARCO_LEGAL.md"
    if p3.exists():
        c = p3.read_text(encoding="utf-8")
        if "logo_include" not in c:
            c = logo_docs + c
            c = c.replace(
                "**PROVEEDOR TECNOLÓGICO**",
                "**PROVEEDOR TECNOLÓGICO: include SOFTWARE STUDIO**"
            )
            p3.write_text(c, encoding="utf-8")
            print("Actualizado:", p3.name)

    # 4. docs/08_PROPUESTA_COMERCIAL_SAAS.md
    p4 = BASE_DIR / "docs" / "08_PROPUESTA_COMERCIAL_SAAS.md"
    if p4.exists():
        c = p4.read_text(encoding="utf-8")
        if "logo_include" not in c:
            c = logo_docs + c.replace(
                "**Versión:** 1.0",
                "**Proveedor Tecnológico:** include SOFTWARE STUDIO  \n**Versión:** 1.3.0 Cloud"
            )
            p4.write_text(c, encoding="utf-8")
            print("Actualizado:", p4.name)

    # 5. docs/09_PROPUESTA_COMERCIAL_SOFTWARE_NATIVO.md
    p5 = BASE_DIR / "docs" / "09_PROPUESTA_COMERCIAL_SOFTWARE_NATIVO.md"
    if p5.exists():
        c = p5.read_text(encoding="utf-8")
        if "logo_include" not in c:
            c = logo_docs + c.replace(
                "**Versión:** 1.0",
                "**Proveedor Tecnológico:** include SOFTWARE STUDIO  \n**Versión:** 1.3.0"
            )
            p5.write_text(c, encoding="utf-8")
            print("Actualizado:", p5.name)

    # 6. docs/ACTA_ENTREGA.md
    p6 = BASE_DIR / "docs" / "ACTA_ENTREGA.md"
    if p6.exists():
        c = p6.read_text(encoding="utf-8")
        if "logo_include" not in c:
            c = logo_docs + c
            c = c.replace(
                "| **Nombre del Proyecto** | Sistema de Gestión de Academia Deportiva |",
                "| **Empresa Desarrolladora** | **include SOFTWARE STUDIO** |\n| **Nombre del Proyecto** | Sistema de Gestión de Academia Deportiva |"
            )
            sig_block = "\n\n| Por el Proveedor Tecnológico | Por la Academia Deportiva |\n| :---: | :---: |\n| <br><br>_______________________________<br><b>include SOFTWARE STUDIO</b><br>Ingeniería y Desarrollo de Software | <br><br>_______________________________<br><b>Dirección General</b><br>Academia Deportiva |\n"
            c = c + sig_block
            p6.write_text(c, encoding="utf-8")
            print("Actualizado:", p6.name)

    # 7. docs/01_DOCUMENTO_GENERAL.md
    p7 = BASE_DIR / "docs" / "01_DOCUMENTO_GENERAL.md"
    if p7.exists():
        c = p7.read_text(encoding="utf-8")
        if "logo_include" not in c:
            c = logo_docs + c.replace(
                "**Versión:** 1.0.0",
                "**Desarrollo:** include SOFTWARE STUDIO  \n**Versión:** 1.3.0 Cloud"
            )
            p7.write_text(c, encoding="utf-8")
            print("Actualizado:", p7.name)

    # 8. docs/INDEX.md
    p8 = BASE_DIR / "docs" / "INDEX.md"
    if p8.exists():
        c = p8.read_text(encoding="utf-8")
        if "logo_include" not in c:
            c = logo_docs + c
            p8.write_text(c, encoding="utf-8")
            print("Actualizado:", p8.name)

    # 9. README.md (root)
    p9 = BASE_DIR / "README.md"
    if p9.exists():
        c = p9.read_text(encoding="utf-8")
        if "logo_include" not in c:
            c = logo_root + c
            footer_readme = "\n\n---\n\n<p align=\"center\">\n  <b>Desarrollado con excelencia por include SOFTWARE STUDIO</b><br>\n  <i>Soluciones de Software y Cloud Computing</i>\n</p>\n"
            c = c + footer_readme
            p9.write_text(c, encoding="utf-8")
            print("Actualizado:", p9.name)

if __name__ == "__main__":
    procesar()
