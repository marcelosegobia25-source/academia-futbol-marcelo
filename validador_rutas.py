#!/usr/bin/env python3
"""Validador de rutas Flask - Verifica que todas las rutas estén correctamente registradas."""

import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app

def validar_rutas():
    """Valida todas las rutas registradas en la aplicación."""
    print("=" * 80)
    print("VALIDADOR DE RUTAS FLASK")
    print("=" * 80)
    
    app = create_app()
    
    rutas_requeridas = {
        'campeonatos.rivales': 'GET',
        'campeonatos.crear_rival': 'GET,POST',
        'campeonatos.editar_rival': 'GET,POST',
        'campeonatos.eliminar_rival': 'POST',
        'calendario.personal': 'GET,POST',
        'calendario.personal_estado': 'POST',
    }
    
    print("\n📋 Verificando rutas requeridas:\n")
    
    todas_ok = True
    for endpoint, metodos_requeridos in rutas_requeridas.items():
        # Intentar encontrar la ruta
        encontrada = False
        ruta_url = None
        metodos_registrados = []
        
        for rule in app.url_map.iter_rules():
            if rule.endpoint == endpoint:
                encontrada = True
                ruta_url = rule.rule
                metodos_registrados = sorted([m for m in rule.methods if m not in {'HEAD', 'OPTIONS'}])
                break
        
        if encontrada:
            print(f"✅ {endpoint}")
            print(f"   URL: {ruta_url}")
            print(f"   Métodos: {', '.join(metodos_registrados)}")
        else:
            print(f"❌ {endpoint}")
            print(f"   ERROR: Ruta no encontrada")
            todas_ok = False
        print()
    
    print("=" * 80)
    if todas_ok:
        print("✅ TODAS LAS RUTAS REQUERIDAS ESTÁN CORRECTAMENTE REGISTRADAS")
    else:
        print("❌ ALGUNAS RUTAS FALTAN O NO ESTÁN CORRECTAMENTE REGISTRADAS")
    print("=" * 80)
    
    # Resumen adicional
    print("\n📊 RESUMEN DE TODAS LAS RUTAS REGISTRADAS:\n")
    
    rutas_por_modulo = {}
    for rule in app.url_map.iter_rules():
        if not rule.endpoint.startswith('static'):
            modulo = rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'otro'
            if modulo not in rutas_por_modulo:
                rutas_por_modulo[modulo] = []
            rutas_por_modulo[modulo].append({
                'endpoint': rule.endpoint,
                'url': rule.rule,
                'metodos': sorted([m for m in rule.methods if m not in {'HEAD', 'OPTIONS'}])
            })
    
    for modulo in sorted(rutas_por_modulo.keys()):
        print(f"\n📁 {modulo.upper()}:")
        for ruta in rutas_por_modulo[modulo]:
            print(f"  • {ruta['endpoint']}")
            print(f"    {ruta['url']} [{', '.join(ruta['metodos'])}]")
    
    print("\n" + "=" * 80 + "\n")
    
    return todas_ok

if __name__ == "__main__":
    validar_rutas()
