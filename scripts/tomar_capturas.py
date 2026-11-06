"""Script para tomar capturas de pantalla de alta resolución de todas las funciones del sistema,
incluyendo las nuevas características de WhatsApp y configuración.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "docs" / "capturas_presentacion"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

PYTHON_EXE = BASE_DIR / ".venv" / "Scripts" / "python.exe"

PAGES_TO_CAPTURE = [
    # (filename, url, description, wait_selector)
    ("01_login.png", "http://127.0.0.1:5000/acceso/", "Pantalla de Acceso Seguro", "form"),
    ("02_dashboard_principal.png", "http://127.0.0.1:5000/informacion/", "Panel de Control y Métricas Ejecutivas", "body"),
    ("03_alumnos_listado.png", "http://127.0.0.1:5000/alumnos/", "Gestión Integral y Listado de Alumnos", "table, .card"),
    ("04_alumnos_nuevo.png", "http://127.0.0.1:5000/alumnos/nuevo", "Formulario de Inscripción y Registro de Deportista", "form"),
    ("05_alumnos_ficha.png", "http://127.0.0.1:5000/alumnos/2", "Ficha Técnica Completa del Deportista", "body"),
    ("06_pagos_control.png", "http://127.0.0.1:5000/pagos/", "Control de Mensualidades y Estados de Cobro", "body"),
    ("07_pagos_nuevo.png", "http://127.0.0.1:5000/pagos/alumno/2/nuevo", "Registro de Cobro y Generación de Recibo", "form"),
    ("08_campeonatos_listado.png", "http://127.0.0.1:5000/campeonatos/", "Directorio de Campeonatos y Torneos", "body"),
    ("09_campeonato_detalle.png", "http://127.0.0.1:5000/campeonatos/1", "Detalle de Torneo, Fixture y Tabla de Posiciones", "body"),
    ("10_campeonato_jugadores.png", "http://127.0.0.1:5000/campeonatos/1/jugadores", "Habilitación y Fichaje de Jugadores en Torneo", "body"),
    ("11_campeonatos_rivales.png", "http://127.0.0.1:5000/campeonatos/rivales", "Directorio de Clubes Rivales", "body"),
    ("12_partidos_programacion.png", "http://127.0.0.1:5000/partidos/", "Programación de Partidos Oficiales y Amistosos", "body"),
    ("13_agenda_eventos.png", "http://127.0.0.1:5000/agenda/", "Agenda Centralizada de Eventos y Partidos", "body"),
    ("14_calendario_mensual.png", "http://127.0.0.1:5000/calendario/", "Calendario Interactivo Mensual y Semanal", "body"),
    ("15_calendario_entrenamientos.png", "http://127.0.0.1:5000/calendario/entrenamientos", "Planificación de Entrenamientos Recurrentes", "body"),
    ("16_asistencia_entrenamiento.png", "http://127.0.0.1:5000/calendario/entrenamientos/1/asistencia", "Control y Planilla de Asistencias a Entrenamientos", "body"),
    ("17_personal_deportivo.png", "http://127.0.0.1:5000/calendario/personal", "Directorio de Personal y Cuerpo Técnico", "body"),
    ("18_categorias.png", "http://127.0.0.1:5000/categorias/", "Configuración de Categorías por Edades", "body"),
    ("19_equipos.png", "http://127.0.0.1:5000/equipos/", "Gestión de Equipos y Divisiones", "body"),
    ("20_lugares_sedes.png", "http://127.0.0.1:5000/lugares/", "Directorio de Complejos Deportivos y Sedes", "body"),
    ("21_usuarios_roles.png", "http://127.0.0.1:5000/usuarios/", "Administración de Usuarios, Roles y Permisos", "body"),
    ("22_auditoria_sistema.png", "http://127.0.0.1:5000/informacion/auditoria", "Módulo de Auditoría Integral y Trazabilidad", "body"),
    ("23_configuracion_academia.png", "http://127.0.0.1:5000/configuracion/", "Configuración Institucional e Identidad Visual", "body"),
    ("26_whatsapp_plantillas.png", "http://127.0.0.1:5000/configuracion/plantillas-whatsapp", "Editor de Plantillas de WhatsApp", "body"),
]

def main():
    print("Iniciando servidor local con base de datos SQLite...")
    env = os.environ.copy()
    env["USE_LOCAL_SQLITE"] = "1"
    servidor = subprocess.Popen(
        [str(PYTHON_EXE), "serve.py"],
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3)  # Esperar inicio de waitress

    try:
        with sync_playwright() as p:
            print("Lanzando navegador...")
            browser = p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True
            )
            context = browser.new_context(
                viewport={"width": 1366, "height": 820},
                device_scale_factor=1.25
            )
            page = context.new_page()

            # 1. Tomar captura de Login
            print("Capturando: 01_login.png")
            page.goto("http://127.0.0.1:5000/acceso/")
            page.wait_for_timeout(1000)
            page.screenshot(path=str(OUTPUT_DIR / "01_login.png"))

            # 2. Iniciar sesión
            print("Iniciando sesión con credenciales de administrador...")
            page.fill("#nombre_usuario", "admin")
            page.fill("#contrasena", "00000")
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            # 3. Capturar el resto de páginas principales
            for filename, url, desc, wait_sel in PAGES_TO_CAPTURE[1:]:
                print(f"Capturando: {filename} - {desc}")
                try:
                    page.goto(url, wait_until="networkidle", timeout=15000)
                    page.wait_for_timeout(800)
                    dest_file = OUTPUT_DIR / filename
                    page.screenshot(path=str(dest_file), full_page=False)
                    print(f"  -> Guardado: {dest_file.name} ({dest_file.stat().st_size // 1024} KB)")
                except Exception as e:
                    print(f"  -> Error al capturar {url}: {e}")

            # 4. Capturar Modal de WhatsApp Individual
            print("Capturando: 24_whatsapp_modal.png - Modal de Mensajería Directa")
            try:
                page.goto("http://127.0.0.1:5000/alumnos/", wait_until="networkidle")
                page.wait_for_timeout(500)
                # Clic en el botón verde de WhatsApp de la primera fila
                btn_wsp = page.locator("button.btn-outline-success[onclick*='abrirModalWhatsApp']").first
                if btn_wsp.count() > 0:
                    btn_wsp.click()
                    page.wait_for_timeout(700)
                    page.screenshot(path=str(OUTPUT_DIR / "24_whatsapp_modal.png"))
                    print("  -> Guardado: 24_whatsapp_modal.png")
                else:
                    print("  -> No se encontró botón individual de WhatsApp")
            except Exception as e:
                print(f"  -> Error capturando modal WhatsApp: {e}")

            # 5. Capturar Modal de Difusión Masiva WhatsApp
            print("Capturando: 25_whatsapp_difusion.png - Modal de Difusión Masiva")
            try:
                page.goto("http://127.0.0.1:5000/alumnos/", wait_until="networkidle")
                page.wait_for_timeout(500)
                btn_dif = page.locator("button:has-text('Mensaje Masivo')").first
                if btn_dif.count() > 0:
                    btn_dif.click()
                    page.wait_for_timeout(700)
                    page.screenshot(path=str(OUTPUT_DIR / "25_whatsapp_difusion.png"))
                    print("  -> Guardado: 25_whatsapp_difusion.png")
                else:
                    print("  -> No se encontró botón de Mensaje Masivo")
            except Exception as e:
                print(f"  -> Error capturando difusión masiva: {e}")

            browser.close()
            print("\nTodas las capturas se completaron exitosamente.")

    finally:
        print("Deteniendo servidor local...")
        servidor.terminate()
        servidor.wait()
        print("Servidor detenido.")

if __name__ == "__main__":
    main()
