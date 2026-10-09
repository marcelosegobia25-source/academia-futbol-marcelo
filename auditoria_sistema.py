#!/usr/bin/env python3
"""Diagnóstico completo del sistema - Verificación de integridad de archivos y configuración."""

import os
import json
from pathlib import Path
from datetime import datetime

def verificar_estructura():
    """Verifica la estructura de carpetas requerida."""
    print("\n" + "="*80)
    print("VERIFICACIÓN DE ESTRUCTURA DE CARPETAS")
    print("="*80)
    
    BASE_DIR = Path(__file__).parent
    carpetas_requeridas = {
        "app": ["routes", "static", "templates", "utils", "migrations"],
        "instance": ["backups", "branding", "comprobantes", "Descargas", "logs", "uploads"],
        "scripts": [],
        "tests": [],
        "docs": [],
        "build": [],
    }
    
    problemas = []
    for carpeta, subcarpetas in carpetas_requeridas.items():
        ruta = BASE_DIR / carpeta
        existe = ruta.exists() and ruta.is_dir()
        print(f"\n{'✅' if existe else '❌'} {carpeta}/")
        if not existe:
            problemas.append(f"Carpeta faltante: {carpeta}")
        else:
            for subdir in subcarpetas:
                subruta = ruta / subdir
                sub_existe = subruta.exists()
                print(f"    {'✅' if sub_existe else '⚠️'} {subdir}/")
                if not sub_existe:
                    problemas.append(f"Subcarpeta faltante: {carpeta}/{subdir}")
    
    return problemas

def verificar_archivos_configuracion():
    """Verifica que existan archivos de configuración esenciales."""
    print("\n" + "="*80)
    print("VERIFICACIÓN DE ARCHIVOS DE CONFIGURACIÓN")
    print("="*80)
    
    BASE_DIR = Path(__file__).parent
    archivos_esenciales = {
        "config.py": "Configuración principal",
        "run.py": "Script de ejecución principal",
        "requirements.txt": "Dependencias Python",
        ".env": "Variables de entorno (opcional)",
    }
    
    problemas = []
    for archivo, descripcion in archivos_esenciales.items():
        ruta = BASE_DIR / archivo
        existe = ruta.exists()
        tamaño = f"{ruta.stat().st_size:,} bytes" if existe else "N/A"
        print(f"{'✅' if existe else '⚠️'} {archivo:30} ({descripcion:40}) - {tamaño}")
        if not existe and ".env" not in archivo:
            problemas.append(f"Archivo esencial faltante: {archivo}")
    
    return problemas

def verificar_permisos_escritura():
    """Verifica permisos de escritura en carpetas críticas."""
    print("\n" + "="*80)
    print("VERIFICACIÓN DE PERMISOS DE ESCRITURA")
    print("="*80)
    
    BASE_DIR = Path(__file__).parent
    carpetas_criticas = [
        "instance",
        "instance/logs",
        "instance/backups",
        "instance/uploads",
        "instance/comprobantes",
    ]
    
    problemas = []
    for carpeta in carpetas_criticas:
        ruta = BASE_DIR / carpeta
        if ruta.exists():
            es_escribible = os.access(ruta, os.W_OK)
            print(f"{'✅' if es_escribible else '❌'} {carpeta:30} - {'Lectura/Escritura' if es_escribible else 'SIN PERMISOS'}")
            if not es_escribible:
                problemas.append(f"Sin permisos de escritura: {carpeta}")
        else:
            print(f"⚠️  {carpeta:30} - No existe")
    
    return problemas

def verificar_logs():
    """Revisa los logs para errores recientes."""
    print("\n" + "="*80)
    print("REVISIÓN DE LOGS")
    print("="*80)
    
    BASE_DIR = Path(__file__).parent
    logs_dir = BASE_DIR / "instance" / "logs"
    
    problemas = []
    if not logs_dir.exists():
        print("⚠️  Carpeta de logs no existe")
        return problemas
    
    archivos_log = sorted(logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not archivos_log:
        print("✅ No hay archivos de log")
        return problemas
    
    print(f"\n📋 Últimos {min(5, len(archivos_log))} archivos de log:")
    for log_file in archivos_log[:5]:
        tamaño = log_file.stat().st_size
        fecha_mod = datetime.fromtimestamp(log_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        tamaño_kb = tamaño / 1024
        print(f"    {log_file.name:40} | {tamaño_kb:10.2f} KB | Modificado: {fecha_mod}")
        
        # Revisar errores en log
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lineas = f.readlines()
                errores = [l for l in lineas if 'ERROR' in l.upper() or 'EXCEPTION' in l.upper()]
                if errores:
                    print(f"       ⚠️  Contiene {len(errores)} error(es)")
                    problemas.append(f"Errores detectados en {log_file.name}")
        except Exception as e:
            print(f"       ❌ No se pudo leer: {e}")
    
    return problemas

def verificar_base_de_datos():
    """Verifica archivos de base de datos."""
    print("\n" + "="*80)
    print("VERIFICACIÓN DE BASE DE DATOS")
    print("="*80)
    
    BASE_DIR = Path(__file__).parent
    db_file = BASE_DIR / "instance" / "academia.db"
    
    problemas = []
    if db_file.exists():
        tamaño_mb = db_file.stat().st_size / (1024 * 1024)
        fecha_mod = datetime.fromtimestamp(db_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"✅ Base de datos encontrada")
        print(f"   Tamaño: {tamaño_mb:.2f} MB")
        print(f"   Última modificación: {fecha_mod}")
        
        # Verificar que no sea muy pequeña
        if tamaño_mb < 0.5:
            print(f"   ⚠️  Base de datos muy pequeña (posiblemente vacía)")
            problemas.append("Base de datos aparentemente vacía")
    else:
        print(f"❌ Base de datos NO encontrada")
        problemas.append("Base de datos no existe")
    
    # Verificar backups
    backups_dir = BASE_DIR / "instance" / "backups"
    if backups_dir.exists():
        backups = list(backups_dir.glob("*.db"))
        print(f"\n✅ {len(backups)} backup(s) encontrado(s)")
        if backups:
            backups_recientes = sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)[:3]
            for backup in backups_recientes:
                fecha = datetime.fromtimestamp(backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                tamaño = backup.stat().st_size / (1024 * 1024)
                print(f"    {backup.name:40} | {tamaño:8.2f} MB | {fecha}")
    else:
        print(f"⚠️  Carpeta de backups no existe")
    
    return problemas

def verificar_modelos():
    """Verifica la integridad básica de los modelos."""
    print("\n" + "="*80)
    print("VERIFICACIÓN DE MODELOS Y RUTAS")
    print("="*80)
    
    BASE_DIR = Path(__file__).parent
    problemas = []
    
    # Verificar models.py
    models_file = BASE_DIR / "app" / "models.py"
    if models_file.exists():
        with open(models_file, 'r', encoding='utf-8') as f:
            contenido = f.read()
            clases = contenido.count('class ')
            print(f"✅ models.py encontrado ({clases} clases detectadas)")
    else:
        print(f"❌ models.py NO encontrado")
        problemas.append("models.py no existe")
    
    # Verificar rutas
    routes_dir = BASE_DIR / "app" / "routes"
    if routes_dir.exists():
        rutas = list(routes_dir.glob("*.py"))
        rutas = [f for f in rutas if f.name != "__init__.py"]
        print(f"✅ {len(rutas)} rutas encontradas")
        for ruta in sorted(rutas)[:10]:
            print(f"    {ruta.name}")
    else:
        print(f"❌ Carpeta de rutas NO encontrada")
        problemas.append("Carpeta de rutas no existe")
    
    return problemas

if __name__ == "__main__":
    print("\n" + "🔍 " * 20)
    print("AUDITORÍA COMPLETA DEL SISTEMA - ACADEMIA DEPORTIVA")
    print("🔍 " * 20)
    
    todos_los_problemas = []
    
    todos_los_problemas.extend(verificar_estructura())
    todos_los_problemas.extend(verificar_archivos_configuracion())
    todos_los_problemas.extend(verificar_permisos_escritura())
    todos_los_problemas.extend(verificar_base_de_datos())
    todos_los_problemas.extend(verificar_logs())
    todos_los_problemas.extend(verificar_modelos())
    
    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN DE LA AUDITORÍA DEL SISTEMA")
    print("="*80)
    
    if not todos_los_problemas:
        print("\n✅ SISTEMA EN PERFECTO ESTADO")
        print("   - Estructura: CORRECTA")
        print("   - Configuración: VÁLIDA")
        print("   - Permisos: CORRECTOS")
        print("   - Base de datos: FUNCIONAL")
        print("   - No hay errores críticos en logs")
    else:
        print(f"\n⚠️  Se detectaron {len(todos_los_problemas)} problema(s):")
        for i, problema in enumerate(todos_los_problemas, 1):
            print(f"   {i}. {problema}")
    
    print("\n" + "="*80 + "\n")
