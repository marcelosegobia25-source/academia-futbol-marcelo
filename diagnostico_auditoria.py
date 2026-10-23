#!/usr/bin/env python3
"""Script de diagnóstico completo de integridad del proyecto."""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.integridad import auditar_sqlite
from config import Config

def diagnostico_integridad():
    """Ejecuta un diagnóstico completo de integridad."""
    print("=" * 80)
    print("DIAGNÓSTICO COMPLETO DE INTEGRIDAD - ACADEMIA DEPORTIVA")
    print("=" * 80)
    
    # Obtener la ruta de la base de datos
    db_path = Config.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
    db_file = Path(db_path)
    
    print(f"\n📊 Información de la Base de Datos:")
    print(f"   Ruta: {db_file}")
    print(f"   Existe: {db_file.exists()}")
    if db_file.exists():
        print(f"   Tamaño: {db_file.stat().st_size / (1024*1024):.2f} MB")
    
    if not db_file.exists():
        print("\n❌ ERROR: La base de datos no existe. Abortando...")
        return
    
    # Ejecutar auditoría
    print(f"\n🔍 Ejecutando auditoría de integridad SQLite...")
    resultado = auditar_sqlite(db_file)
    
    # Resumen general
    print(f"\n{'='*80}")
    print("RESUMEN GENERAL:")
    print(f"{'='*80}")
    print(f"✓ Estado de integridad: {resultado['integridad']}")
    print(f"✓ Auditoría completada: {'SÍ' if resultado['integridad'] != 'no ejecutada' else 'NO'}")
    print(f"✓ Estado general: {'CORRECTO' if resultado['correcta'] else 'CON PROBLEMAS'}")
    print(f"✓ Total de tablas: {len(resultado['tablas'])}")
    
    # Tablas y registros
    print(f"\n{'='*80}")
    print("ESTADÍSTICAS DE TABLAS:")
    print(f"{'='*80}")
    for tabla in sorted(resultado['tablas']):
        registros = resultado['estadisticas'].get(tabla, 0)
        print(f"   {tabla:30} | {registros:10,d} registros")
    
    # Problemas estructurales
    print(f"\n{'='*80}")
    print("PROBLEMAS ESTRUCTURALES:")
    print(f"{'='*80}")
    
    if resultado['sin_pk']:
        print(f"\n⚠️  Tablas sin Clave Primaria ({len(resultado['sin_pk'])}):")
        for tabla in resultado['sin_pk']:
            print(f"    - {tabla}")
    else:
        print("\n✅ Todas las tablas tienen clave primaria")
    
    if resultado['fks_invalidas']:
        print(f"\n❌ Referencias Foráneas Inválidas ({len(resultado['fks_invalidas'])}):")
        for fk in resultado['fks_invalidas']:
            print(f"    - Tabla: {fk['table']}, Columna: {fk['rowid']}")
            print(f"      Referencia inválida: {fk['fkid']}")
    else:
        print("\n✅ Todas las referencias foráneas son válidas")
    
    if resultado['duplicados_partidos']:
        print(f"\n⚠️  Partidos Posiblemente Duplicados ({len(resultado['duplicados_partidos'])}):")
        for dup in resultado['duplicados_partidos']:
            print(f"    - IDs: {dup['ids']} | Cantidad: {dup['cantidad']}")
            print(f"      Fecha: {dup['fecha']} Hora: {dup['hora']}")
    else:
        print("\n✅ No hay partidos duplicados")
    
    # Problemas de integridad lógica
    print(f"\n{'='*80}")
    print("ALERTAS DE INTEGRIDAD LÓGICA:")
    print(f"{'='*80}")
    
    if resultado['alertas']:
        print(f"\n❌ Se detectaron {len(resultado['alertas'])} problemas:")
        for i, alerta in enumerate(resultado['alertas'], 1):
            print(f"    {i}. {alerta}")
    else:
        print("\n✅ No hay alertas de integridad lógica")
    
    # Índices recomendados
    print(f"\n{'='*80}")
    print("ÍNDICES RECOMENDADOS:")
    print(f"{'='*80}")
    
    if resultado['indices_recomendados']:
        print(f"\n⚠️  Se recomiendan {len(resultado['indices_recomendados'])} índices:")
        for idx in resultado['indices_recomendados']:
            print(f"    - {idx}")
    else:
        print("\n✅ Índices están bien configurados")
    
    # Conclusión
    print(f"\n{'='*80}")
    print("CONCLUSIÓN:")
    print(f"{'='*80}")
    if resultado['correcta']:
        print("\n✅ LA BASE DE DATOS ESTÁ EN PERFECTO ESTADO")
        print("   - Integridad SQLite: CORRECTA")
        print("   - Estructura: VÁLIDA")
        print("   - Referencias: CONSISTENTES")
        print("   - Datos: SIN INCONSISTENCIAS")
    else:
        print("\n⚠️  SE DETECTARON PROBLEMAS EN LA BASE DE DATOS")
        problemas = []
        if resultado['sin_pk']:
            problemas.append(f"   - {len(resultado['sin_pk'])} tabla(s) sin clave primaria")
        if resultado['fks_invalidas']:
            problemas.append(f"   - {len(resultado['fks_invalidas'])} referencia(s) foránea(s) inválida(s)")
        if resultado['alertas']:
            problemas.append(f"   - {len(resultado['alertas'])} inconsistencia(s) lógica(s)")
        if resultado['duplicados_partidos']:
            problemas.append(f"   - {len(resultado['duplicados_partidos'])} posible(s) duplicado(s)")
        for problema in problemas:
            print(problema)
        print("\n   Se recomienda ejecutar 'python scripts/reparar_integridad_auditoria.py'")
    
    print(f"\n{'='*80}\n")
    return resultado

if __name__ == "__main__":
    diagnostico_integridad()
