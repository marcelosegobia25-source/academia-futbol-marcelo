"""Restaurador gráfico de la base de datos del sistema de academias."""

import os
import shutil
import sqlite3
import socket
import sys
import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from tkinter import Tk, messagebox


NOMBRE_BASE = "academia.db"


def ruta_recurso(nombre):
    raiz = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return raiz / nombre


def validar_base(ruta):
    conexion = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=10)
    try:
        integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
        if integridad != "ok":
            raise RuntimeError(f"Integridad inválida: {integridad}")
        tablas = {
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        requeridas = {"alumno", "pago", "configuracion"}
        if not requeridas.issubset(tablas):
            raise RuntimeError("El archivo no corresponde al sistema de gestión de academias.")
        alumnos = conexion.execute("SELECT count(1) FROM alumno").fetchone()[0]
        pagos = conexion.execute("SELECT count(1) FROM pago").fetchone()[0]
        return alumnos, pagos
    finally:
        conexion.close()


def aplicacion_abierta():
    """Detecta el sistema por su proceso, sin confundir otras apps en el puerto 5000."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as comprobador:
        comprobador.settimeout(0.4)
        if comprobador.connect_ex(("127.0.0.1", 5000)) == 0:
            return True
    if os.name != "nt":
        return False

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(wintypes.ULONG)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        return False

    entrada = PROCESSENTRY32W()
    entrada.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    encontrado = False
    try:
        continuar = kernel32.Process32FirstW(snapshot, ctypes.byref(entrada))
        while continuar:
            if entrada.szExeFile.casefold() == "academiafutbol.exe":
                encontrado = True
                break
            continuar = kernel32.Process32NextW(snapshot, ctypes.byref(entrada))
    finally:
        kernel32.CloseHandle(snapshot)
    return encontrado


def respaldar_existente(origen, destino):
    conexion_origen = sqlite3.connect(str(origen), timeout=10)
    conexion_destino = sqlite3.connect(str(destino))
    try:
        conexion_origen.backup(conexion_destino)
        if conexion_destino.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("No se pudo validar el respaldo preventivo.")
    finally:
        conexion_destino.close()
        conexion_origen.close()


def restaurar():
    raiz = Tk()
    raiz.withdraw()
    try:
        incluida = ruta_recurso(NOMBRE_BASE)
        alumnos, pagos = validar_base(incluida)

        if aplicacion_abierta():
            messagebox.showwarning(
                "Sistema de Gestión de Academias",
                "Cierre completamente el Sistema de Gestión de Academias y vuelva a "
                "ejecutar este restaurador.",
                parent=raiz,
            )
            return 2

        if not messagebox.askyesno(
            "Restaurar base de datos",
            "Se restaurará la copia de prueba en este equipo.\n\n"
            f"Alumnos: {alumnos}\nPagos: {pagos}\n\n"
            "Si ya existe una base, se guardará un respaldo automático antes "
            "de reemplazarla.\n\n¿Desea continuar?",
            parent=raiz,
        ):
            return 0

        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("Windows no informó la carpeta LOCALAPPDATA.")

        carpeta_datos = Path(local_app_data) / "GestionAcademiaDeportiva"
        carpeta_datos.mkdir(parents=True, exist_ok=True)
        destino = carpeta_datos / NOMBRE_BASE
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        respaldo = None

        if destino.exists():
            carpeta_respaldos = carpeta_datos / "backups"
            carpeta_respaldos.mkdir(parents=True, exist_ok=True)
            respaldo = carpeta_respaldos / f"academia_antes_restaurar_{marca}.db"
            respaldar_existente(destino, respaldo)

        temporal = carpeta_datos / f".academia_restaurando_{marca}.db"
        shutil.copy2(incluida, temporal)
        validar_base(temporal)
        os.replace(temporal, destino)

        # La aplicación está cerrada; estos archivos podrían pertenecer a la
        # base anterior y SQLite los recreará de forma segura al iniciar.
        for sufijo in ("-wal", "-shm"):
            auxiliar = Path(str(destino) + sufijo)
            if auxiliar.exists():
                auxiliar.unlink()

        detalle_respaldo = (
            f"\n\nRespaldo anterior:\n{respaldo}" if respaldo else ""
        )
        messagebox.showinfo(
            "Restauración completada",
            "La base de datos fue restaurada correctamente.\n\n"
            "Ya puede abrir el Sistema de Gestión de Academias."
            f"{detalle_respaldo}",
            parent=raiz,
        )
        return 0
    except Exception as error:
        messagebox.showerror(
            "No se pudo restaurar",
            f"No se realizó la restauración.\n\nDetalle: {error}",
            parent=raiz,
        )
        return 1
    finally:
        raiz.destroy()


if __name__ == "__main__":
    raise SystemExit(restaurar())
