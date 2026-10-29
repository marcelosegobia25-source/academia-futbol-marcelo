#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sembrador Maestro de Todos los Escenarios y Módulos de la Academia de Fútbol.

Puebla la base de datos con escenarios exhaustivos y realistas:
1. Seguridad: Roles ampliados y usuarios para cada área.
2. Infraestructura: Sedes y canchas principales.
3. Categorías y Equipos: Divisiones completas, equipos propios y rivales.
4. Personal Deportivo: Entrenadores, preparadores y cuerpo técnico.
5. Alumnos y Tutores: 24+ alumnos cubriendo TODOS los estados:
   - Activos al día (diversas categorías y turnos)
   - Próximos a vencer (3 y 5 días de aviso)
   - Vencidos / Morosos (1 y 2 meses de mora)
   - Con pago parcial (saldo pendiente)
   - Becados 100% (Excelencia y Vulnerabilidad)
   - Becados 50% (Hermanitos)
   - Becados 25% (Convenio)
   - Retirados con fecha y motivo
   - Reactivados tras retiro
   - Con pago anulado y reemplazado con trazabilidad
   - Fichas completas: posiciones, piernas, turnos, medidas, tutores y parentescos.
6. Pagos y Cobranzas:
   - Tarifas por categoría
   - Obligaciones, pagos en Efectivo y QR
   - Abonos parciales
   - Pago anulado formalmente con registro en AnulacionPago y reemplazo
7. Tienda e Inventario:
   - Proveedores registrados con NIT
   - Productos con variantes de tallas y colores
   - Compras con facturas que ingresaron stock
   - Ventas normales, con descuento, con devolución parcial y anuladas
   - Conteo de inventario aprobado y pendiente
8. Finanzas y Pagos Programados:
   - Movimientos de ingresos y egresos
   - Pagos programados (alquiler, entrenadores, mantenimiento con cuota omitida)
9. Deporte y Competición:
   - Torneo Apertura 2026 (En curso) con fixture, partidos jugados y programados, tabla de posiciones
   - Copa Relámpago Verano 2026 (Finalizado) con podio oficial (1º, 2º y 3º)
   - Entrenamientos semanales y sesiones con asistencias (Presente, Ausente, Justificado, Tarde)
10. Bitácora de Auditoría completa.
"""

import sys
from pathlib import Path
from datetime import date, datetime, time as dtime, timedelta
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import create_app
from app.extensions import db
from app.models import (
    Usuario, Rol, Permiso, Categoria, Equipo, Alumno, Tutor, AlumnoTutor,
    InscripcionGestion, Obligacion, Pago, AplicacionPago, Tarifa, BecaHistorial,
    AnulacionPago, CierreCaja, SesionCaja, MovimientoCaja, Proveedor,
    CategoriaContable, MovimientoContable, Producto, ProductoVariante,
    MovimientoInventario, ConteoInventario, DetalleConteoInventario,
    Compra, DetalleCompra, Venta, DetalleVenta, DevolucionVenta, DetalleDevolucionVenta,
    PagoProgramado, CuotaProgramada, Lugar, PersonalDeportivo, Entrenamiento,
    SesionEntrenamiento, AsistenciaEntrenamiento, Campeonato, Partido,
    PodioCampeonato, Posicion, AlumnoCampeonato, Auditoria,
    HistorialCategoriaAlumno, HistorialEquipoAlumno, HistorialAlumno
)
from app.utils.autorizacion import CATEGORIAS_PERMISOS


def sembrar_todos_los_escenarios():
    print("=" * 80)
    print("INICIANDO SIEMBRA MAESTRA DE TODOS LOS ESCENARIOS EN TODOS LOS MÓDULOS")
    print("=" * 80)

    app = create_app()
    with app.app_context():
        hoy = date.today()
        hace_30 = hoy - timedelta(days=30)
        hace_60 = hoy - timedelta(days=60)
        hace_90 = hoy - timedelta(days=90)
        mes_actual = hoy.strftime("%Y-%m")
        mes_anterior = (hoy.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        mes_hace_dos = (hoy.replace(day=1) - timedelta(days=32)).strftime("%Y-%m")
        mes_siguiente = (hoy.replace(day=28) + timedelta(days=5)).strftime("%Y-%m")

        # ----------------------------------------------------------------------
        # 1. SEGURIDAD: PERMISOS, ROLES Y USUARIOS
        # ----------------------------------------------------------------------
        print("\n[1/10] Configurando Permisos, Roles y Usuarios...")
        permisos_db = {}
        for categoria, lista in CATEGORIAS_PERMISOS.items():
            for cod, nom, desc in lista:
                p = Permiso.query.filter_by(codigo=cod).first()
                if not p:
                    p = Permiso(codigo=cod, nombre=nom, descripcion=desc)
                    db.session.add(p)
                    db.session.flush()
                permisos_db[cod] = p

        roles_config = {
            "Administrador": {
                "desc": "Acceso total a todos los módulos y configuraciones del sistema.",
                "permisos": list(permisos_db.keys())
            },
            "Secretaría": {
                "desc": "Atención al público, inscripciones, cobros y asistencia deportiva.",
                "permisos": [
                    "ver_alumnos", "gestionar_alumnos", "gestionar_becas",
                    "ver_pagos", "registrar_pagos", "gestionar_asistencia", "ver_deportivo"
                ]
            },
            "Cobranzas": {
                "desc": "Cobro de cuotas mensuales, control de deudores y emisión de recibos.",
                "permisos": [
                    "ver_alumnos", "ver_pagos", "registrar_pagos", "anular_pagos"
                ]
            },
            "Profesor": {
                "desc": "Planificación de entrenamientos, asistencia y control de partidos.",
                "permisos": [
                    "ver_alumnos", "ver_deportivo", "gestionar_asistencia"
                ]
            },
            "Coordinador Deportivo": {
                "desc": "Dirección deportiva, torneos, fixture, canchas y seguimiento de planteles.",
                "permisos": [
                    "ver_alumnos", "gestionar_alumnos", "ver_deportivo",
                    "gestionar_deportivo", "gestionar_equipos",
                    "gestionar_lugares", "gestionar_asistencia"
                ]
            }
        }

        roles_db = {}
        for r_nom, r_info in roles_config.items():
            r = Rol.query.filter_by(nombre=r_nom).first()
            if not r:
                r = Rol(nombre=r_nom, descripcion=r_info["desc"])
                db.session.add(r)
                db.session.flush()
            else:
                r.descripcion = r_info["desc"]

            # Asignar permisos
            r.permisos = [permisos_db[c] for c in r_info["permisos"] if c in permisos_db]
            roles_db[r_nom] = r

        db.session.flush()

        # Usuarios para cada rol
        usuarios_data = [
            ("admin", "Daniel Admin (Director General)", "Administrador"),
            ("secretaria_laura", "Laura Paredes (Secretaría General)", "Secretaría"),
            ("cobranzas_diego", "Diego Morales (Cobranzas)", "Cobranzas"),
            ("profe_carlos", "Prof. Carlos Méndez (DT Sub-11 y Sub-13)", "Profesor"),
            ("profe_mateo", "Prof. Mateo Rojas (DT Sub-7 y Sub-9)", "Profesor"),
            ("coordinador_raul", "Prof. Raúl Gutiérrez (Coordinador Deportivo)", "Coordinador Deportivo"),
            ("auxiliar_pedro", "Pedro Salinas (Auxiliar Administrativo)", "Secretaría"),
        ]

        usuarios_db = {}
        for login, nombre_comp, rol_nom in usuarios_data:
            u = Usuario.query.filter_by(nombre_usuario=login).first()
            if not u:
                u = Usuario(
                    nombre_usuario=login,
                    nombre_completo=nombre_comp,
                    id_rol=roles_db[rol_nom].id_rol,
                    activo=True,
                    debe_cambiar_clave=False
                )
                u.establecer_contrasena("00000")
                db.session.add(u)
                db.session.flush()
            else:
                u.nombre_completo = nombre_comp
                u.id_rol = roles_db[rol_nom].id_rol
                u.activo = True
            usuarios_db[login] = u

        db.session.flush()
        print(f"  -> {len(roles_db)} roles y {len(usuarios_db)} usuarios listos.")

        # ----------------------------------------------------------------------
        # 2. SEDES Y CANCHAS (LUGARES)
        # ----------------------------------------------------------------------
        print("\n[2/10] Registrando Sedes y Canchas...")
        lugares_data = [
            ("Cancha Principal - Césped Natural", "Cancha", "Av. Costanera N° 450", "Césped natural reglamentario con iluminación nocturna", 1500, "Césped Natural"),
            ("Cancha Sintética Techada Norte", "Cancha", "Calle Los Pinos N° 120", "Cancha sintética techada para fútbol 7 y formativo", 400, "Césped Sintético"),
            ("Complejo Polideportivo Municipal", "Polideportivo", "Av. Juan Pablo II N° 800", "Complejo auxiliar para torneos interdepartamentales", 2500, "Sintético / Mixto"),
        ]
        lugares_db = {}
        for nom, tipo, dirn, desc, cap, sup in lugares_data:
            lug = Lugar.query.filter_by(nombre=nom).first()
            if not lug:
                lug = Lugar(
                    nombre=nom,
                    tipo=tipo,
                    direccion=dirn,
                    capacidad=cap,
                    superficie=sup,
                    activo=True
                )
                db.session.add(lug)
                db.session.flush()
            lugares_db[nom] = lug

        # ----------------------------------------------------------------------
        # 3. CATEGORÍAS Y EQUIPOS (PROPIOS Y RIVALES)
        # ----------------------------------------------------------------------
        print("\n[3/10] Creando Categorías y Equipos...")
        cat_definitions = [
            ("7", 6, 7),
            ("9", 8, 9),
            ("11", 10, 11),
            ("13", 12, 13),
            ("15", 14, 15),
            ("Femenino", None, None),
        ]
        categorias_db = {}
        for nom, e_min, e_max in cat_definitions:
            cat = Categoria.query.filter_by(nombre=nom).first()
            if not cat:
                cat = Categoria(nombre=nom, edad_min=e_min, edad_max=e_max)
                db.session.add(cat)
                db.session.flush()
            categorias_db[nom] = cat

        equipos_propios = [
            ("Semillero Sub-7", "7"),
            ("Halcones Sub-9", "9"),
            ("Tigres Sub-11", "11"),
            ("Leones Sub-13", "13"),
            ("Águilas Sub-15", "15"),
            ("Estrellas Femenino", "Femenino"),
        ]
        equipos_db = {}
        for eq_nom, cat_k in equipos_propios:
            cat_obj = categorias_db[cat_k]
            eq = Equipo.query.filter_by(nombre=eq_nom, es_rival=False).first()
            if not eq:
                eq = Equipo(nombre=eq_nom, id_categoria=cat_obj.id_categoria, es_rival=False, activo=True)
                db.session.add(eq)
                db.session.flush()
            equipos_db[eq_nom] = eq

        equipos_rivales = [
            ("Academia Tahuichi Rival", "9"),
            ("Bolívar Junior Filial", "11"),
            ("The Strongest Formativo", "13"),
            ("Club Aurora Jr", "15"),
            ("San José Cantera", "11"),
        ]
        for eq_nom, cat_k in equipos_rivales:
            cat_obj = categorias_db[cat_k]
            eq = Equipo.query.filter_by(nombre=eq_nom, es_rival=True).first()
            if not eq:
                eq = Equipo(nombre=eq_nom, id_categoria=cat_obj.id_categoria, es_rival=True, activo=True)
                db.session.add(eq)
                db.session.flush()
            equipos_db[eq_nom] = eq

        # ----------------------------------------------------------------------
        # 4. PERSONAL DEPORTIVO (CUERPO TÉCNICO)
        # ----------------------------------------------------------------------
        print("\n[4/10] Registrando Personal Deportivo...")
        personal_data = [
            ("Prof. Carlos Méndez", "7894561", "71234567", "carlos@academia.com", "Entrenador", "Fútbol Formativo Sub-11 y Sub-13"),
            ("Prof. Mateo Rojas", "6541238", "72345678", "mateo@academia.com", "Entrenador", "Iniciación y Semillero Sub-7 / Sub-9"),
            ("Prof. Raúl Gutiérrez", "5412398", "73456789", "raul@academia.com", "Director Técnico", "Coordinación y Juveniles Sub-15"),
            ("Lic. Laura Paredes", "4781256", "74567890", "laura.prep@academia.com", "Preparador físico", "Acondicionamiento y Plantel Femenino"),
        ]
        personal_db = {}
        for nom, doc, tel, cor, tipo, esp in personal_data:
            p = PersonalDeportivo.query.filter_by(documento=doc).first()
            if not p:
                p = PersonalDeportivo(
                    nombre=nom,
                    documento=doc,
                    telefono=tel,
                    correo=cor,
                    tipo=tipo,
                    especialidad=esp,
                    fecha_ingreso=date(2025, 1, 15),
                    activo=True
                )
                db.session.add(p)
                db.session.flush()
            personal_db[nom] = p

        # ----------------------------------------------------------------------
        # 5. TARIFAS POR CATEGORÍA
        # ----------------------------------------------------------------------
        print("\n[5/10] Configurando Tarifas Oficiales...")
        tarifas_def = [
            ("7", Decimal("130.00")),
            ("9", Decimal("130.00")),
            ("11", Decimal("150.00")),
            ("13", Decimal("150.00")),
            ("15", Decimal("160.00")),
            ("Femenino", Decimal("140.00")),
        ]
        tarifas_db = {}
        for cat_k, monto in tarifas_def:
            c_obj = categorias_db[cat_k]
            tar = Tarifa.query.filter_by(concepto="Mensualidad", id_categoria=c_obj.id_categoria, activo=True).first()
            if not tar:
                tar = Tarifa(
                    concepto="Mensualidad",
                    monto=monto,
                    fecha_inicio=date(2026, 1, 1),
                    id_categoria=c_obj.id_categoria,
                    activo=True
                )
                db.session.add(tar)
                db.session.flush()
            tarifas_db[cat_k] = tar

        # ----------------------------------------------------------------------
        # 6. TUTORES FORMALES
        # ----------------------------------------------------------------------
        print("\n[6/10] Registrando Tutores Familiares...")
        tutores_data = [
            ("Roberto Fernández", "4567891", "78912345", "roberto.f@email.com", "Av. San Martín #120"),
            ("Elena Quiroga Morales", "5678912", "79823456", "elena.q@email.com", "Calle Sucre #45"),
            ("Gonzalo Torrico Vaca", "6789123", "71298345", "gonzalo.t@email.com", "Condominio Las Palmas B-12"),
            ("Patricia Morales Soliz", "7891234", "72349812", "patricia.m@email.com", "Av. Circunvalación #890"),
            ("Marco Guzmán Peña", "8912345", "73451298", "marco.g@email.com", "Calle Bolívar #310"),
            ("Carla Paz Saucedo", "9123456", "74562391", "carla.p@email.com", "Barrio Urbarí #23"),
            ("Ing. Jorge Flores", "3456789", "75673412", "jorge.f@email.com", "Calle Los Sauces #77"),
            ("Dra. Silvia Ruiz", "2345678", "76784523", "silvia.r@email.com", "Av. Alemania #450"),
            ("Ramiro Castro", "1234567", "77895634", "ramiro.c@email.com", "Av. Banzer Km 6"),
            ("Gladys Benítez", "9876543", "78906745", "gladys.b@email.com", "Calle Murillo #512"),
            ("Hernán Silva", "8765432", "79017856", "hernan.s@email.com", "Barrio Equipetrol #105"),
            ("Valeria Vega", "7654321", "70128967", "valeria.v@email.com", "Av. Mutualista #33"),
            ("Lic. Carlos Zeballos", "6543210", "71239078", "carlos.z@email.com", "Av. Santos Dumont #220"),
            ("Martha Mamani Choque", "5432109", "72340189", "martha.m@email.com", "Plan 3000 Curva #12"),
            ("Oscar Cordero Méndez", "4321098", "73451290", "oscar.c@email.com", "Villa 1ro de Mayo #88"),
            ("Mariana Pinto", "3210987", "74562301", "mariana.p@email.com", "Av. Roca y Coronado #500"),
            ("Fernando Rojas", "2109876", "75673412", "fernando.r@email.com", "Calle Cochabamba #412"),
            ("Andrea Choque", "1098765", "76784523", "andrea.ch@email.com", "Av. Virgen de Cotoca #90"),
        ]
        tutores_db = {}
        for nom, doc, tel, cor, dirn in tutores_data:
            t = Tutor.query.filter_by(documento=doc).first()
            if not t:
                t = Tutor(nombre=nom, documento=doc, telefono=tel, correo=cor, direccion=dirn, activo=True)
                db.session.add(t)
                db.session.flush()
            tutores_db[nom] = t

        # ----------------------------------------------------------------------
        # 7. ALUMNOS CON TODOS LOS ESCENARIOS POSIBLES
        # ----------------------------------------------------------------------
        print("\n[7/10] Generando Alumnos representativos de TODOS los escenarios...")
        
        # Estructura del caso:
        # (nombre, apellido, ci, fecha_nac, cat_k, equipo_k, pos, pierna, peso, alt, sexo, beca_tipo, beca_pct, turno, tutor_nom, parentesco, escenario_clave)
        escenarios_alumnos = [
            # 1. AL DÍA - Sub-9
            ("Matías", "Fernández", "1001001", date(2017, 4, 12), "9", "Halcones Sub-9", "DEL", "Derecha", 28.5, 1.28, "M", "Ninguna", 0, "Mañana", "Roberto Fernández", "Padre", "al_dia_sub9"),
            # 2. AL DÍA - Sub-11
            ("Lucas", "Quiroga Morales", "1001002", date(2015, 8, 22), "11", "Tigres Sub-11", "MED", "Izquierda", 35.0, 1.40, "M", "Ninguna", 0, "Tarde", "Elena Quiroga Morales", "Madre", "al_dia_sub11"),
            # 3. AL DÍA - Sub-13
            ("Gabriel", "Torrico Vaca", "1001003", date(2013, 2, 10), "13", "Leones Sub-13", "DEF", "Derecha", 48.0, 1.55, "M", "Ninguna", 0, "Tarde", "Gonzalo Torrico Vaca", "Padre", "al_dia_sub13"),
            # 4. AL DÍA - Sub-15
            ("Alejandro", "Morales Soliz", "1001004", date(2011, 11, 5), "15", "Águilas Sub-15", "DEL", "Ambas", 58.5, 1.68, "M", "Ninguna", 0, "Noche", "Patricia Morales Soliz", "Madre", "al_dia_sub15"),
            # 5. AL DÍA - Femenino
            ("Valentina", "Guzmán Peña", "1001005", date(2013, 6, 18), "Femenino", "Estrellas Femenino", "MED", "Derecha", 42.0, 1.50, "F", "Ninguna", 0, "Mañana", "Marco Guzmán Peña", "Padre", "al_dia_fem"),
            # 6. AL DÍA - Sub-7
            ("Thiago", "Paz Saucedo", "1001006", date(2019, 3, 30), "7", "Semillero Sub-7", "DEL", "Derecha", 22.0, 1.15, "M", "Ninguna", 0, "Mañana", "Carla Paz Saucedo", "Madre", "al_dia_sub7"),
            
            # 7. PRÓXIMO A VENCER (Vence en 3 días)
            ("Benjamín", "Flores Méndez", "1001007", date(2015, 5, 14), "11", "Tigres Sub-11", "DEF", "Derecha", 36.5, 1.42, "M", "Ninguna", 0, "Tarde", "Ing. Jorge Flores", "Padre", "proximo_vencer_3d"),
            # 8. PRÓXIMO A VENCER (Vence en 5 días)
            ("Sebastián", "Ruiz Soliz", "1001008", date(2017, 9, 8), "9", "Halcones Sub-9", "POR", "Derecha", 30.0, 1.32, "M", "Ninguna", 0, "Mañana", "Dra. Silvia Ruiz", "Madre", "proximo_vencer_5d"),
            
            # 9. VENCIDO / MOROSO LEVE (1 mes impago - Marzo pendiente)
            ("Nicolás", "Castro Banzer", "1001009", date(2013, 7, 19), "13", "Leones Sub-13", "MED", "Izquierda", 46.0, 1.52, "M", "Ninguna", 0, "Tarde", "Ramiro Castro", "Padre", "moroso_1_mes"),
            # 10. MOROSO CRÍTICO (2 meses impagos - Febrero y Marzo)
            ("Franco", "Benítez Murillo", "1001010", date(2011, 4, 25), "15", "Águilas Sub-15", "DEF", "Derecha", 61.0, 1.72, "M", "Ninguna", 0, "Noche", "Gladys Benítez", "Madre", "moroso_2_meses"),
            
            # 11. PAGO PARCIAL CON SALDO (Obligación de 130 Bs, abonó 70 Bs, debe 60 Bs)
            ("Emiliano", "Silva Equipetrol", "1001011", date(2017, 12, 1), "9", "Halcones Sub-9", "DEL", "Derecha", 27.0, 1.25, "M", "Ninguna", 0, "Mañana", "Hernán Silva", "Padre", "pago_parcial_efectivo"),
            # 12. PAGO PARCIAL CON SALDO QR (Obligación de 150 Bs, abonó 100 Bs por QR, debe 50 Bs)
            ("Joaquín", "Vega Mutualista", "1001012", date(2015, 10, 11), "11", "Tigres Sub-11", "MED", "Ambas", 34.0, 1.38, "M", "Ninguna", 0, "Tarde", "Valeria Vega", "Madre", "pago_parcial_qr"),
            
            # 13. BECADO 100% (Excelencia Deportiva - Selección Departamental)
            ("Andrés", "Zeballos Santos", "1001013", date(2013, 3, 15), "13", "Leones Sub-13", "DEL", "Izquierda", 44.0, 1.56, "M", "Completa", 100, "Tarde", "Lic. Carlos Zeballos", "Padre", "beca_100_talento"),
            # 14. BECADO 100% (Vulnerabilidad Económica y Social)
            ("Diego", "Mamani Choque", "1001014", date(2015, 6, 2), "11", "Tigres Sub-11", "MED", "Derecha", 33.0, 1.36, "M", "Completa", 100, "Mañana", "Martha Mamani Choque", "Madre", "beca_100_social"),
            
            # 15. BECADO 50% (Hermanitos en la academia - Hermano Mayor)
            ("Álvaro", "Cordero Méndez", "1001015", date(2013, 9, 20), "13", "Leones Sub-13", "DEF", "Derecha", 47.0, 1.54, "M", "Media", 50, "Tarde", "Oscar Cordero Méndez", "Padre", "beca_50_hermano_mayor"),
            # 16. BECADO 50% (Hermanitos en la academia - Hermano Menor)
            ("Bruno", "Cordero Méndez", "1001016", date(2017, 1, 14), "9", "Halcones Sub-9", "DEL", "Derecha", 29.0, 1.30, "M", "Media", 50, "Tarde", "Oscar Cordero Méndez", "Padre", "beca_50_hermano_menor"),
            
            # 17. BECADO 25% (Convenio Colegio Alemán)
            ("Samuel", "Pinto Coronado", "1001017", date(2015, 2, 28), "11", "Tigres Sub-11", "POR", "Derecha", 38.0, 1.45, "M", "Media", 25, "Mañana", "Mariana Pinto", "Madre", "beca_25_convenio"),
            
            # 18. RETIRADO DEFINITIVO (Mudanza de ciudad)
            ("Maximiliano", "Rojas Cochabamba", "1001018", date(2013, 5, 10), "13", "Leones Sub-13", "MED", "Derecha", 45.0, 1.51, "M", "Ninguna", 0, "Tarde", "Fernando Rojas", "Padre", "retirado_mudanza"),
            # 19. RETIRADO POR LESIÓN
            ("Cristian", "Herrera Rodilla", "1001019", date(2011, 8, 30), "15", "Águilas Sub-15", "DEF", "Derecha", 64.0, 1.75, "M", "Ninguna", 0, "Noche", "Fernando Rojas", "Tío", "retirado_lesion"),
            
            # 20. REACTIVADO TRAS RETIRO
            ("Daniel", "Choque Cotoca", "1001020", date(2015, 12, 5), "11", "Tigres Sub-11", "DEL", "Izquierda", 36.0, 1.41, "M", "Ninguna", 0, "Tarde", "Andrea Choque", "Madre", "reactivado_ok"),
            
            # 21. CON PAGO ANULADO Y REEMPLAZADO FORMALMENTE
            ("Rodrigo", "Vaca Trazabilidad", "1001021", date(2013, 10, 8), "13", "Leones Sub-13", "MED", "Derecha", 49.0, 1.57, "M", "Ninguna", 0, "Tarde", "Gonzalo Torrico Vaca", "Tutor Legal", "con_pago_anulado"),
            
            # 22. ASIGNACIÓN MANUAL DE CATEGORÍA POR RENDIMIENTO
            ("Leonardo", "Suárez Promesa", "1001022", date(2015, 1, 20), "13", "Leones Sub-13", "DEL", "Ambas", 39.0, 1.48, "M", "Ninguna", 0, "Tarde", "Roberto Fernández", "Tío", "categoria_manual"),
            
            # 23. PORTERO DESTACADO SUB-15
            ("Rodrigo", "Mendizábal Gigante", "1001023", date(2011, 2, 14), "15", "Águilas Sub-15", "POR", "Izquierda", 68.0, 1.83, "M", "Ninguna", 0, "Noche", "Patricia Morales Soliz", "Tía", "arquero_sub15"),
            
            # 24. CAPITANA FEMENINO
            ("Camila", "Navarro Líder", "1001024", date(2013, 4, 5), "Femenino", "Estrellas Femenino", "DEL", "Derecha", 43.5, 1.53, "F", "Ninguna", 0, "Mañana", "Elena Quiroga Morales", "Tía", "capitana_fem"),
        ]

        alumnos_creados = {}
        for (nom, ape, ci, fnac, cat_k, eq_k, pos, pierna, peso, alt, sexo,
             beca_t, beca_pct, turno, tutor_nom, paren, esc_clave) in escenarios_alumnos:
            
            cat_obj = categorias_db[cat_k]
            eq_obj = equipos_db[eq_k]
            tutor_obj = tutores_db[tutor_nom]
            
            es_retirado = "retirado" in esc_clave
            es_reactivado = "reactivado" in esc_clave
            es_manual = "categoria_manual" in esc_clave
            
            alu = Alumno.query.filter_by(ci=ci).first()
            if not alu:
                alu = Alumno(
                    nombre=nom,
                    apellido=ape,
                    ci=ci,
                    fecha_nacimiento=fnac,
                    id_categoria=cat_obj.id_categoria,
                    categoria_manual=es_manual,
                    estado="Retirado" if es_retirado else "Activo",
                    posicion=pos,
                    pierna_habil=pierna,
                    peso=peso,
                    estatura=alt,
                    sexo=sexo,
                    beca=beca_t,
                    beca_fecha_fin=date(2026, 12, 31) if beca_t != "Ninguna" else None,
                    turno=turno,
                    tutor=tutor_nom,
                    telefono=tutor_obj.telefono,
                    direccion=tutor_obj.direccion,
                    fecha_retiro=hace_30 if es_retirado else None,
                    fecha_ultima_reactivacion=hace_30 if es_reactivado else None,
                    fecha_base_pago=hace_90
                )
                alu.equipos = [eq_obj]
                db.session.add(alu)
                db.session.flush()

                # Vínculo con Tutor
                db.session.add(AlumnoTutor(
                    id_alumno=alu.id_alumno,
                    id_tutor=tutor_obj.id_tutor,
                    parentesco=paren,
                    principal=True,
                    autorizado_recoger=True
                ))

                # Inscripción 2026
                tarifa_base = tarifas_db[cat_k].monto
                db.session.add(InscripcionGestion(
                    id_alumno=alu.id_alumno,
                    gestion=2026,
                    fecha_inscripcion=date(2026, 1, 10),
                    fecha_fin=hace_30 if es_retirado else None,
                    estado="Retirada" if es_retirado else "Activa",
                    id_categoria=cat_obj.id_categoria,
                    id_equipo_principal=eq_obj.id_equipo,
                    id_tarifa=tarifas_db[cat_k].id_tarifa,
                    monto_tarifa=tarifa_base,
                    porcentaje_beca=Decimal(str(beca_pct)),
                    observacion=f"Escenario: {esc_clave}"
                ))

                # Historial de Categoría y Equipo
                db.session.add(HistorialCategoriaAlumno(
                    id_alumno=alu.id_alumno,
                    id_categoria=cat_obj.id_categoria,
                    fecha_inicio=date(2026, 1, 10),
                    tipo_asignacion="Manual" if es_manual else "Automática",
                    motivo="Rendimiento sobresaliente" if es_manual else "Inscripción regular"
                ))
                db.session.add(HistorialEquipoAlumno(
                    id_alumno=alu.id_alumno,
                    id_equipo=eq_obj.id_equipo,
                    gestion=2026,
                    fecha_inicio=date(2026, 1, 10),
                    estado="Baja" if es_retirado else "Activa",
                    principal=True
                ))

                # Si tiene beca, registrar historial formal
                if beca_pct > 0:
                    db.session.add(BecaHistorial(
                        id_alumno=alu.id_alumno,
                        porcentaje=Decimal(str(beca_pct)),
                        fecha_inicio=date(2026, 1, 1),
                        fecha_fin=date(2026, 12, 31),
                        motivo=f"Beca {beca_pct}% asignada por dirección deportiva",
                        autorizado_por="Daniel Admin",
                        estado="Activa"
                    ))

            alumnos_creados[esc_clave] = alu

        db.session.flush()
        print(f"  -> {len(alumnos_creados)} alumnos con todos sus perfiles vinculados correctamente.")

        # ----------------------------------------------------------------------
        # 8. OBLIGACIONES Y PAGOS (CUBRIENDO TODOS LOS ESTADOS DE MENSUALIDAD)
        # ----------------------------------------------------------------------
        print("\n[8/10] Generando Flujo de Pagos, Recibos y Obligaciones...")
        
        # Función auxiliar para crear Obligación
        def crear_obligacion(alu, periodo, f_venc, tarifa_monto, beca_pct=0):
            ob = Obligacion.query.filter_by(id_alumno=alu.id_alumno, concepto="Mensualidad", periodo=periodo).first()
            if not ob:
                monto_orig = tarifa_monto
                desc = (monto_orig * Decimal(str(beca_pct)) / Decimal("100")).quantize(Decimal("0.01"))
                cubierto = (beca_pct >= 100)
                ob = Obligacion(
                    id_alumno=alu.id_alumno,
                    concepto="Mensualidad",
                    periodo=periodo,
                    monto_original=monto_orig,
                    descuento=desc,
                    recargo=Decimal("0.00"),
                    cubierto_beca=cubierto,
                    fecha_vencimiento=f_venc
                )
                db.session.add(ob)
                db.session.flush()
            return ob

        def crear_pago_con_recibo(alu, ob, f_pago, f_venc, monto, modo, num_op, anulado=False, motivo_anul=None):
            p = Pago.query.filter_by(id_alumno=alu.id_alumno, mes_pagado=ob.periodo, numero_operacion=num_op).first()
            if not p:
                p = Pago(
                    id_alumno=alu.id_alumno,
                    es_beca=ob.cubierto_beca,
                    fecha_pago=f_pago,
                    fecha_vencimiento=f_venc,
                    mes_pagado=ob.periodo,
                    modo_pago=modo,
                    monto=Decimal(str(monto)),
                    numero_operacion=num_op,
                    eliminado_en=datetime.now() if anulado else None
                )
                db.session.add(p)
                db.session.flush()

                if not anulado:
                    db.session.add(AplicacionPago(
                        id_obligacion=ob.id_obligacion,
                        id_pago=p.id_pago,
                        monto=Decimal(str(monto))
                    ))
                elif motivo_anul:
                    db.session.add(AnulacionPago(
                        id_pago=p.id_pago,
                        motivo=motivo_anul
                    ))
                    db.session.add(Auditoria(
                        modulo="Pagos",
                        accion="ANULACION_PAGO",
                        entidad="Pago",
                        id_entidad=p.id_pago,
                        detalle=f"Pago #{p.id_pago} anulado: {motivo_anul} (Alumno: {alu.nombre_completo}, Recibo: {num_op})"
                    ))
            return p

        # 1. Alumnos Al Día: Pagos de Enero, Febrero, Marzo y cobertura vigente
        for clave in ["al_dia_sub9", "al_dia_sub11", "al_dia_sub13", "al_dia_sub15", "al_dia_fem", "al_dia_sub7"]:
            alu = alumnos_creados[clave]
            tarifa = tarifas_db[alu.categoria.nombre].monto
            # Enero
            ob_ene = crear_obligacion(alu, "2026-01", date(2026, 1, 20), tarifa)
            crear_pago_con_recibo(alu, ob_ene, date(2026, 1, 12), date(2026, 2, 12), tarifa, "Efectivo", f"REC-2026-{alu.id_alumno:03d}-01")
            # Febrero
            ob_feb = crear_obligacion(alu, "2026-02", date(2026, 2, 20), tarifa)
            crear_pago_con_recibo(alu, ob_feb, date(2026, 2, 10), date(2026, 3, 10), tarifa, "QR", f"QR-BCP-{alu.id_alumno:03d}-02")
            # Marzo (Vigente, pagado a tiempo)
            ob_mar = crear_obligacion(alu, "2026-03", date(2026, 3, 20), tarifa)
            crear_pago_con_recibo(alu, ob_mar, date(2026, 3, 8), hoy + timedelta(days=20), tarifa, "Efectivo", f"REC-2026-{alu.id_alumno:03d}-03")

        # 2. Próximos a Vencer (cobertura vence en 3 y 5 días)
        alu_p3 = alumnos_creados["proximo_vencer_3d"]
        tar_p3 = tarifas_db[alu_p3.categoria.nombre].monto
        ob_p3 = crear_obligacion(alu_p3, mes_actual, hoy + timedelta(days=3), tar_p3)
        crear_pago_con_recibo(alu_p3, ob_p3, hoy - timedelta(days=27), hoy + timedelta(days=3), tar_p3, "Efectivo", f"REC-PROX-3D-{alu_p3.id_alumno}")

        alu_p5 = alumnos_creados["proximo_vencer_5d"]
        tar_p5 = tarifas_db[alu_p5.categoria.nombre].monto
        ob_p5 = crear_obligacion(alu_p5, mes_actual, hoy + timedelta(days=5), tar_p5)
        crear_pago_con_recibo(alu_p5, ob_p5, hoy - timedelta(days=25), hoy + timedelta(days=5), tar_p5, "QR", f"QR-PROX-5D-{alu_p5.id_alumno}")

        # 3. Moroso Leve (1 mes pendiente - Marzo)
        alu_m1 = alumnos_creados["moroso_1_mes"]
        tar_m1 = tarifas_db[alu_m1.categoria.nombre].monto
        ob_m1_feb = crear_obligacion(alu_m1, mes_anterior, hoy - timedelta(days=35), tar_m1)
        crear_pago_con_recibo(alu_m1, ob_m1_feb, hoy - timedelta(days=60), hoy - timedelta(days=30), tar_m1, "Efectivo", f"REC-FEB-{alu_m1.id_alumno}")
        # Marzo sin pagar:
        crear_obligacion(alu_m1, mes_actual, hoy - timedelta(days=10), tar_m1)

        # 4. Moroso Crítico (2 meses pendientes - Febrero y Marzo)
        alu_m2 = alumnos_creados["moroso_2_meses"]
        tar_m2 = tarifas_db[alu_m2.categoria.nombre].monto
        crear_obligacion(alu_m2, mes_hace_dos, hoy - timedelta(days=45), tar_m2)
        crear_obligacion(alu_m2, mes_anterior, hoy - timedelta(days=15), tar_m2)

        # 5. Pago Parcial en Efectivo (Obligación de 130, paga 70, debe 60)
        alu_par1 = alumnos_creados["pago_parcial_efectivo"]
        ob_par1 = crear_obligacion(alu_par1, mes_actual, hoy + timedelta(days=15), Decimal("130.00"))
        crear_pago_con_recibo(alu_par1, ob_par1, hoy - timedelta(days=2), hoy + timedelta(days=15), Decimal("70.00"), "Efectivo", f"REC-PARC-{alu_par1.id_alumno}")

        # 6. Pago Parcial en QR (Obligación de 150, paga 100 por QR, debe 50)
        alu_par2 = alumnos_creados["pago_parcial_qr"]
        ob_par2 = crear_obligacion(alu_par2, mes_actual, hoy + timedelta(days=15), Decimal("150.00"))
        crear_pago_con_recibo(alu_par2, ob_par2, hoy - timedelta(days=1), hoy + timedelta(days=15), Decimal("100.00"), "QR", f"QR-PARC-{alu_par2.id_alumno}")

        # 7. Becados 100% (Obligaciones cubiertas por beca)
        for clave in ["beca_100_talento", "beca_100_social"]:
            alu_b = alumnos_creados[clave]
            tar_b = tarifas_db[alu_b.categoria.nombre].monto
            crear_obligacion(alu_b, mes_anterior, hoy - timedelta(days=20), tar_b, beca_pct=100)
            crear_obligacion(alu_b, mes_actual, hoy + timedelta(days=15), tar_b, beca_pct=100)

        # 8. Becados 50% y 25%
        for clave, pct in [("beca_50_hermano_mayor", 50), ("beca_50_hermano_menor", 50), ("beca_25_convenio", 25)]:
            alu_b = alumnos_creados[clave]
            tar_b = tarifas_db[alu_b.categoria.nombre].monto
            ob_b = crear_obligacion(alu_b, mes_actual, hoy + timedelta(days=18), tar_b, beca_pct=pct)
            monto_neto = ob_b.total
            crear_pago_con_recibo(alu_b, ob_b, hoy - timedelta(days=5), hoy + timedelta(days=18), monto_neto, "QR", f"QR-BECA-{alu_b.id_alumno}")

        # 9. Caso con Pago Anulado y Reemplazado
        alu_anul = alumnos_creados["con_pago_anulado"]
        tar_anul = tarifas_db[alu_anul.categoria.nombre].monto
        ob_anul = crear_obligacion(alu_anul, mes_actual, hoy + timedelta(days=20), tar_anul)
        
        # Pago erróneo cobrado por 300 Bs que se anula
        p_erroneo = crear_pago_con_recibo(
            alu_anul, ob_anul, hoy - timedelta(days=3), hoy + timedelta(days=20),
            Decimal("300.00"), "Efectivo", f"REC-ERR-{alu_anul.id_alumno}",
            anulado=True, motivo_anul="Error de digitación al cobrar cuota: se cobró 300 Bs en vez de 150 Bs."
        )
        # Pago correcto de reemplazo por 150 Bs
        p_reemplazo = crear_pago_con_recibo(
            alu_anul, ob_anul, hoy - timedelta(days=3), hoy + timedelta(days=20),
            Decimal("150.00"), "Efectivo", f"REC-CORR-{alu_anul.id_alumno}"
        )
        # Vincular reemplazo en AnulacionPago
        if p_erroneo.anulacion:
            p_erroneo.anulacion.id_pago_reemplazo = p_reemplazo.id_pago

        db.session.flush()
        print("  -> Obligaciones, pagos normales, abonos parciales y anulaciones registrados.")

        # ----------------------------------------------------------------------
        # 9. TIENDA, INVENTARIO Y MOVIMIENTOS CONTABLES
        # ----------------------------------------------------------------------
        print("\n[9/10] Creando Tienda, Proveedores, Inventario y Contabilidad...")
        
        # Categorías Contables
        cat_contables = [
            ("Mensualidades", "Ingreso"),
            ("Inscripciones y Matrícula", "Ingreso"),
            ("Venta Indumentaria y Tienda", "Ingreso"),
            ("Premios y Torneos", "Ingreso"),
            ("Alquiler de Canchas e Instalaciones", "Egreso"),
            ("Honorarios Entrenadores", "Egreso"),
            ("Material y Equipamiento Deportivo", "Egreso"),
            ("Botiquín y Primeros Auxilios", "Egreso"),
            ("Arbitrajes y Planillaje", "Egreso"),
            ("Devoluciones de Tienda", "Egreso"),
        ]
        cat_contables_db = {}
        for nom, tipo in cat_contables:
            cc = CategoriaContable.query.filter_by(nombre=nom).first()
            if not cc:
                cc = CategoriaContable(nombre=nom, tipo=tipo, activo=True)
                db.session.add(cc)
                db.session.flush()
            cat_contables_db[nom] = cc

        # Proveedores
        prov_data = [
            ("Textiles & Confecciones Golazo SRL", "Empresa", "1029384021", "77012345", "ventas@golazo.com", "Lic. Sonia Ramos"),
            ("Balones & Redes Sudamérica", "Empresa", "9382019482", "77098765", "contacto@balonessur.com", "Ing. Fernando Ortiz"),
            ("Médica Deportiva & Ortopedia", "Empresa", "8291039014", "77045678", "medica@deportiva.com", "Dra. Claudia Soliz"),
        ]
        prov_db = {}
        for nom, tipo, doc, tel, cor, cont in prov_data:
            pr = Proveedor.query.filter_by(nombre=nom).first()
            if not pr:
                pr = Proveedor(nombre=nom, tipo_persona=tipo, documento=doc, telefono=tel, correo=cor, contacto=cont, activo=True)
                db.session.add(pr)
                db.session.flush()
            prov_db[nom] = pr

        # Productos e Inventario
        prod_data = [
            ("Camiseta Oficial Titular", "CAM-OFIC", "Uniformes", [
                ("8", "Verde/Negro", 50, 90, 15, 5),
                ("10", "Verde/Negro", 50, 90, 18, 5),
                ("12", "Verde/Negro", 55, 100, 20, 5),
                ("14", "Verde/Negro", 55, 100, 14, 5),
                ("S", "Verde/Negro", 60, 110, 12, 4),
                ("M", "Verde/Negro", 60, 110, 10, 4),
                ("L", "Verde/Negro", 65, 120, 8, 3),
            ]),
            ("Short Oficial Competencia", "SHT-OFIC", "Uniformes", [
                ("8", "Blanco", 30, 55, 20, 5),
                ("10", "Blanco", 30, 55, 22, 5),
                ("12", "Blanco", 35, 60, 18, 5),
                ("14", "Blanco", 35, 60, 15, 5),
                ("S", "Blanco", 40, 70, 12, 4),
                ("M", "Blanco", 40, 70, 10, 4),
            ]),
            ("Medias Oficiales de Fútbol", "MED-OFIC", "Accesorios", [
                ("Junior", "Verde", 15, 30, 45, 10),
                ("Senior", "Verde", 18, 35, 30, 10),
            ]),
            ("Balón Entrenamiento Nº 4", "BAL-N4", "Equipamiento", [
                ("Nº 4", "Blanco/Verde", 75, 130, 25, 5),
            ]),
            ("Balón Competición Nº 5 FIFA Basic", "BAL-N5", "Equipamiento", [
                ("Nº 5", "Blanco/Azul", 95, 160, 18, 5),
            ]),
            ("Canilleras Ergonómicas", "CAN-ERG", "Protección", [
                ("S", "Negro", 25, 50, 20, 5),
                ("M", "Negro", 25, 50, 15, 5),
            ]),
        ]

        variantes_db = {}
        for p_nom, p_cod, p_cat, vars_list in prod_data:
            prod = Producto.query.filter_by(codigo=p_cod).first()
            if not prod:
                prod = Producto(nombre=p_nom, codigo=p_cod, categoria=p_cat, activo=True)
                db.session.add(prod)
                db.session.flush()
            
            for talla, color, p_comp, p_vent, stock_i, s_min in vars_list:
                var = ProductoVariante.query.filter_by(id_producto=prod.id_producto, talla=talla, color=color).first()
                if not var:
                    var = ProductoVariante(
                        id_producto=prod.id_producto,
                        talla=talla,
                        color=color,
                        precio_compra=Decimal(str(p_comp)),
                        precio_venta=Decimal(str(p_vent)),
                        stock=stock_i,
                        stock_minimo=s_min
                    )
                    db.session.add(var)
                    db.session.flush()
                variantes_db[f"{p_cod}_{talla}_{color}"] = var

        # Compras a Proveedores
        prov_textiles = prov_db["Textiles & Confecciones Golazo SRL"]
        compra1 = Compra.query.filter_by(numero_factura="FAC-GOLAZO-2026-001").first()
        if not compra1:
            var_cam_10 = variantes_db["CAM-OFIC_10_Verde/Negro"]
            var_sht_10 = variantes_db["SHT-OFIC_10_Blanco"]
            compra1 = Compra(
                id_proveedor=prov_textiles.id_proveedor,
                fecha=hace_30,
                numero_factura="FAC-GOLAZO-2026-001",
                modo_pago="Transferencia",
                total=Decimal("2000.00"),
                observacion="Dotación inicial temporada 2026 de camisetas y shorts formativos"
            )
            db.session.add(compra1)
            db.session.flush()
            db.session.add(DetalleCompra(compra=compra1, variante=var_cam_10, cantidad=25, costo_unitario=Decimal("50.00"), subtotal=Decimal("1250.00")))
            db.session.add(DetalleCompra(compra=compra1, variante=var_sht_10, cantidad=25, costo_unitario=Decimal("30.00"), subtotal=Decimal("750.00")))

        # Ventas a Alumnos con diversos escenarios
        alu_matias = alumnos_creados["al_dia_sub9"]
        var_cam_10 = variantes_db["CAM-OFIC_10_Verde/Negro"]
        var_sht_10 = variantes_db["SHT-OFIC_10_Blanco"]
        var_med_jr = variantes_db["MED-OFIC_Junior_Verde"]

        # Venta 1: Venta normal en Efectivo de uniforme completo
        v1 = Venta.query.filter_by(numero_operacion="TKT-2026-001").first()
        if not v1:
            v1 = Venta(
                id_alumno=alu_matias.id_alumno,
                fecha=hace_30 + timedelta(days=2),
                modo_pago="Efectivo",
                numero_operacion="TKT-2026-001",
                subtotal=Decimal("175.00"),
                descuento=Decimal("0.00"),
                total=Decimal("175.00"),
                observacion="Venta indumentaria oficial completa"
            )
            db.session.add(v1)
            db.session.flush()
            db.session.add(DetalleVenta(venta=v1, variante=var_cam_10, cantidad=1, precio_unitario=Decimal("90.00"), subtotal=Decimal("90.00")))
            db.session.add(DetalleVenta(venta=v1, variante=var_sht_10, cantidad=1, precio_unitario=Decimal("55.00"), subtotal=Decimal("55.00")))
            db.session.add(DetalleVenta(venta=v1, variante=var_med_jr, cantidad=1, precio_unitario=Decimal("30.00"), subtotal=Decimal("30.00")))

        # Venta 2: Venta con descuento especial
        alu_lucas = alumnos_creados["al_dia_sub11"]
        v2 = Venta.query.filter_by(numero_operacion="TKT-2026-002").first()
        if not v2:
            v2 = Venta(
                id_alumno=alu_lucas.id_alumno,
                fecha=hace_30 + timedelta(days=5),
                modo_pago="QR",
                numero_operacion="TKT-2026-002",
                subtotal=Decimal("200.00"),
                descuento=Decimal("20.00"),
                total=Decimal("180.00"),
                observacion="Descuento especial por pago al contado kit entrenamiento"
            )
            db.session.add(v2)
            db.session.flush()

        # Venta 3: Venta con Devolución Parcial (Cambio por talla o ajuste)
        alu_gabriel = alumnos_creados["al_dia_sub13"]
        v3 = Venta.query.filter_by(numero_operacion="TKT-2026-003").first()
        if not v3:
            v3 = Venta(
                id_alumno=alu_gabriel.id_alumno,
                fecha=hace_30 + timedelta(days=10),
                modo_pago="Efectivo",
                numero_operacion="TKT-2026-003",
                subtotal=Decimal("60.00"),
                descuento=Decimal("0.00"),
                total=Decimal("60.00"),
                observacion="Venta de 2 pares de medias"
            )
            db.session.add(v3)
            db.session.flush()
            det_v3 = DetalleVenta(venta=v3, variante=var_med_jr, cantidad=2, precio_unitario=Decimal("30.00"), subtotal=Decimal("60.00"))
            db.session.add(det_v3)
            db.session.flush()

            # Devolución de 1 par
            dev = DevolucionVenta(
                id_venta=v3.id_venta,
                fecha=hace_30 + timedelta(days=12),
                tipo="Devolución",
                total_credito=Decimal("30.00"),
                motivo="Devolución de 1 par por talla incorrecta"
            )
            db.session.add(dev)
            db.session.flush()
            db.session.add(DetalleDevolucionVenta(
                id_devolucion=dev.id_devolucion,
                id_detalle_venta=det_v3.id_detalle,
                cantidad=1,
                subtotal=Decimal("30.00")
            ))

        # Venta 4: Venta Anulada
        v4 = Venta.query.filter_by(numero_operacion="TKT-2026-004").first()
        if not v4:
            v4 = Venta(
                id_alumno=None,
                cliente_externo="Sr. Carlos Vendedor Externo",
                fecha=hace_30 + timedelta(days=15),
                modo_pago="Efectivo",
                numero_operacion="TKT-2026-004",
                subtotal=Decimal("130.00"),
                descuento=Decimal("0.00"),
                total=Decimal("130.00"),
                observacion="Venta de balón cancelada",
                anulado_en=datetime.now(),
                motivo_anulacion="Cliente desistió de la compra antes de retirar el balón"
            )
            db.session.add(v4)
            db.session.flush()

        # Conteos de Inventario (Aprobado y Pendiente)
        if not ConteoInventario.query.filter_by(observacion="Conteo mensual de cierre febrero 2026").first():
            conteo_aprob = ConteoInventario(
                fecha=date(2026, 2, 28),
                estado="Aprobado",
                observacion="Conteo mensual de cierre febrero 2026"
            )
            db.session.add(conteo_aprob)
            db.session.flush()
            db.session.add(DetalleConteoInventario(conteo=conteo_aprob, variante=var_cam_10, stock_sistema=var_cam_10.stock, stock_contado=var_cam_10.stock))
            db.session.add(DetalleConteoInventario(conteo=conteo_aprob, variante=var_sht_10, stock_sistema=var_sht_10.stock, stock_contado=var_sht_10.stock))

        if not ConteoInventario.query.filter_by(observacion="Conteo quincenal marzo 2026").first():
            conteo_pend = ConteoInventario(
                fecha=hoy - timedelta(days=2),
                estado="Pendiente",
                observacion="Conteo quincenal marzo 2026"
            )
            db.session.add(conteo_pend)
            db.session.flush()
            db.session.add(DetalleConteoInventario(conteo=conteo_pend, variante=var_med_jr, stock_sistema=var_med_jr.stock, stock_contado=var_med_jr.stock - 1))

        # Pagos Programados (Alquiler, Entrenadores, Mantenimiento con cuota omitida)
        prov_cancha = prov_db["Textiles & Confecciones Golazo SRL"]
        p_prog1 = PagoProgramado.query.filter_by(concepto="Alquiler mensual Cancha Principal").first()
        if not p_prog1:
            p_prog1 = PagoProgramado(
                concepto="Alquiler mensual Cancha Principal",
                categoria="Alquiler de Canchas e Instalaciones",
                id_categoria_contable=cat_contables_db["Alquiler de Canchas e Instalaciones"].id_categoria_contable,
                monto=Decimal("1200.00"),
                id_proveedor=prov_cancha.id_proveedor,
                modo_pago="Transferencia",
                frecuencia="Mensual",
                dia_mes=30,
                fecha_inicio=date(2026, 1, 1),
                proxima_fecha=date(2026, 4, 30),
                activo=True
            )
            db.session.add(p_prog1)
            db.session.flush()
            # Cuotas de enero y febrero pagadas, marzo pendiente
            db.session.add(CuotaProgramada(id_programado=p_prog1.id_programado, fecha_vencimiento=date(2026, 1, 30), monto=Decimal("1200.00"), estado="Pagado", fecha_pago=date(2026, 1, 29)))
            db.session.add(CuotaProgramada(id_programado=p_prog1.id_programado, fecha_vencimiento=date(2026, 2, 28), monto=Decimal("1200.00"), estado="Pagado", fecha_pago=date(2026, 2, 27)))
            db.session.add(CuotaProgramada(id_programado=p_prog1.id_programado, fecha_vencimiento=date(2026, 3, 30), monto=Decimal("1200.00"), estado="Pendiente"))

        p_prog2 = PagoProgramado.query.filter_by(concepto="Mantenimiento preventivo césped").first()
        if not p_prog2:
            p_prog2 = PagoProgramado(
                concepto="Mantenimiento preventivo césped",
                categoria="Material y Equipamiento Deportivo",
                id_categoria_contable=cat_contables_db["Material y Equipamiento Deportivo"].id_categoria_contable,
                monto=Decimal("300.00"),
                modo_pago="Efectivo",
                frecuencia="Mensual",
                dia_mes=15,
                fecha_inicio=date(2026, 1, 15),
                proxima_fecha=date(2026, 4, 15),
                activo=True
            )
            db.session.add(p_prog2)
            db.session.flush()
            db.session.add(CuotaProgramada(id_programado=p_prog2.id_programado, fecha_vencimiento=date(2026, 1, 15), monto=Decimal("300.00"), estado="Pagado", fecha_pago=date(2026, 1, 15)))
            db.session.add(CuotaProgramada(id_programado=p_prog2.id_programado, fecha_vencimiento=date(2026, 2, 15), monto=Decimal("300.00"), estado="Omitido", motivo_omision="Servicio suspendido por lluvia continua en toda la quincena"))
            db.session.add(CuotaProgramada(id_programado=p_prog2.id_programado, fecha_vencimiento=date(2026, 3, 15), monto=Decimal("300.00"), estado="Pagado", fecha_pago=date(2026, 3, 15)))

        # ----------------------------------------------------------------------

        # ----------------------------------------------------------------------
        # 10. DEPORTE: CAMPEONATOS, FIXTURE, POSICIONES, PODIOS Y ASISTENCIAS
        # ----------------------------------------------------------------------
        print("\n[10/10] Generando Campeonatos, Fixture, Resultados y Asistencias...")
        
        cancha_ppal = lugares_db["Cancha Principal - Césped Natural"]
        cancha_sint = lugares_db["Cancha Sintética Techada Norte"]
        
        # 1. Torneo Apertura 2026 (En Curso)
        torneo_apert = Campeonato.query.filter_by(nombre="Torneo Apertura Infantil 2026").first()
        if not torneo_apert:
            torneo_apert = Campeonato(
                nombre="Torneo Apertura Infantil 2026",
                fecha_inicio=date(2026, 2, 1),
                fecha_fin=date(2026, 5, 30),
                lugar="Cancha Principal - Césped Natural",
                id_lugar=cancha_ppal.id_lugar,
                estado="En curso",
                formato="Liga",
                vueltas=1,
                clasificados=4,
                puntos_victoria=3,
                puntos_empate=1,
                puntos_derrota=0,
                tercer_puesto=True
            )
            torneo_apert.categorias = [categorias_db["9"], categorias_db["11"], categorias_db["13"]]
            torneo_apert.equipos = [
                equipos_db["Halcones Sub-9"],
                equipos_db["Tigres Sub-11"],
                equipos_db["Leones Sub-13"],
                equipos_db["Academia Tahuichi Rival"],
                equipos_db["Bolívar Junior Filial"],
                equipos_db["The Strongest Formativo"],
            ]
            db.session.add(torneo_apert)
            db.session.flush()

            # Partidos Jugados y Finalizados
            partidos_data = [
                # Partido 1: Halcones Sub-9 (3) vs Academia Tahuichi (1)
                (date(2026, 2, 14), dtime(9, 0), cancha_ppal.nombre, cancha_ppal.id_lugar,
                 equipos_db["Halcones Sub-9"].id_equipo, equipos_db["Academia Tahuichi Rival"].id_equipo,
                 categorias_db["9"].id_categoria, "Academia Tahuichi Rival", "Finalizado", 3, 1, "Victoria sólida con doblete de Matías Fernández"),
                
                # Partido 2: Tigres Sub-11 (2) vs Bolívar Junior Filial (2)
                (date(2026, 2, 21), dtime(10, 30), cancha_sint.nombre, cancha_sint.id_lugar,
                 equipos_db["Tigres Sub-11"].id_equipo, equipos_db["Bolívar Junior Filial"].id_equipo,
                 categorias_db["11"].id_categoria, "Bolívar Junior Filial", "Finalizado", 2, 2, "Empate intenso en el último minuto"),
                
                # Partido 3: Leones Sub-13 (4) vs The Strongest Formativo (0)
                (date(2026, 2, 28), dtime(11, 45), cancha_ppal.nombre, cancha_ppal.id_lugar,
                 equipos_db["Leones Sub-13"].id_equipo, equipos_db["The Strongest Formativo"].id_equipo,
                 categorias_db["13"].id_categoria, "The Strongest Formativo", "Finalizado", 4, 0, "Gran actuación colectiva y valla invicta"),
                
                # Partido 4: Bolívar Junior (1) vs The Strongest Formativo (2)
                (date(2026, 3, 7), dtime(10, 0), cancha_ppal.nombre, cancha_ppal.id_lugar,
                 equipos_db["Bolívar Junior Filial"].id_equipo, equipos_db["The Strongest Formativo"].id_equipo,
                 categorias_db["11"].id_categoria, "The Strongest Formativo", "Finalizado", 1, 2, "Clásico disputado con goles de media distancia"),

                # Partido 5 (Futuro): Halcones Sub-9 vs Bolívar Junior Filial
                (hoy + timedelta(days=5), dtime(9, 30), cancha_ppal.nombre, cancha_ppal.id_lugar,
                 equipos_db["Halcones Sub-9"].id_equipo, equipos_db["Bolívar Junior Filial"].id_equipo,
                 categorias_db["9"].id_categoria, "Bolívar Junior Filial", "Programado", None, None, "Fecha 4 por la cima de la tabla"),

                # Partido 6 (Futuro): Tigres Sub-11 vs Academia Tahuichi Rival
                (hoy + timedelta(days=6), dtime(11, 0), cancha_sint.nombre, cancha_sint.id_lugar,
                 equipos_db["Tigres Sub-11"].id_equipo, equipos_db["Academia Tahuichi Rival"].id_equipo,
                 categorias_db["11"].id_categoria, "Academia Tahuichi Rival", "Programado", None, None, "Duelo clave de la división"),
            ]

            for f_part, h_part, c_nom, c_id, id_eq, id_riv, id_cat, riv_nom, est_p, g_loc, g_vis, obs in partidos_data:
                db.session.add(Partido(
                    fecha=f_part,
                    hora=h_part,
                    cancha=c_nom,
                    id_lugar=c_id,
                    id_equipo=id_eq,
                    id_equipo_rival=id_riv,
                    id_categoria=id_cat,
                    rival=riv_nom,
                    id_campeonato=torneo_apert.id_campeonato,
                    fase="Liga",
                    jornada=1,
                    estado_partido=est_p,
                    goles_local=g_loc,
                    goles_visita=g_vis,
                    resultado=f"{g_loc} - {g_vis}" if g_loc is not None else None,
                    observacion=obs
                ))

            # Tabla de Posiciones para Sub-9
            pos_sub9 = [
                (equipos_db["Halcones Sub-9"], 1, 1, 0, 0, 3, 1),
                (equipos_db["Academia Tahuichi Rival"], 1, 0, 0, 1, 1, 3),
            ]
            for eq_obj, pj, pg, pe, pp, gf, gc in pos_sub9:
                db.session.add(Posicion(
                    id_campeonato=torneo_apert.id_campeonato,
                    id_categoria=categorias_db["9"].id_categoria,
                    id_equipo=eq_obj.id_equipo,
                    pj=pj, pg=pg, pe=pe, pp=pp, gf=gf, gc=gc
                ))

            # Tabla de Posiciones para Sub-11
            pos_sub11 = [
                (equipos_db["The Strongest Formativo"], 1, 1, 0, 0, 2, 1),
                (equipos_db["Tigres Sub-11"], 1, 0, 1, 0, 2, 2),
                (equipos_db["Bolívar Junior Filial"], 2, 0, 1, 1, 3, 4),
            ]
            for eq_obj, pj, pg, pe, pp, gf, gc in pos_sub11:
                db.session.add(Posicion(
                    id_campeonato=torneo_apert.id_campeonato,
                    id_categoria=categorias_db["11"].id_categoria,
                    id_equipo=eq_obj.id_equipo,
                    pj=pj, pg=pg, pe=pe, pp=pp, gf=gf, gc=gc
                ))

        # 2. Copa Relámpago Verano 2026 (Finalizado con Podio)
        copa_verano = Campeonato.query.filter_by(nombre="Copa Relámpago Verano 2026").first()
        if not copa_verano:
            copa_verano = Campeonato(
                nombre="Copa Relámpago Verano 2026",
                fecha_inicio=date(2026, 1, 15),
                fecha_fin=date(2026, 1, 28),
                lugar="Cancha Sintética Techada Norte",
                id_lugar=cancha_sint.id_lugar,
                estado="Finalizado",
                formato="Eliminación directa",
                vueltas=1,
                clasificados=4,
                puntos_victoria=3,
                puntos_empate=1,
                puntos_derrota=0,
                tercer_puesto=True,
                finalizado_en=datetime(2026, 1, 28, 18, 0),
                motivo_cierre="Torneo finalizado con entrega oficial de trofeos y medallas"
            )
            copa_verano.categorias = [categorias_db["9"], categorias_db["11"]]
            copa_verano.equipos = [
                equipos_db["Halcones Sub-9"],
                equipos_db["Tigres Sub-11"],
                equipos_db["Bolívar Junior Filial"],
                equipos_db["Academia Tahuichi Rival"]
            ]
            db.session.add(copa_verano)
            db.session.flush()

            # Podio Oficial
            db.session.add(PodioCampeonato(
                id_campeonato=copa_verano.id_campeonato,
                id_categoria=categorias_db["9"].id_categoria,
                id_campeon=equipos_db["Halcones Sub-9"].id_equipo,
                id_subcampeon=equipos_db["Bolívar Junior Filial"].id_equipo,
                id_tercero=equipos_db["Tigres Sub-11"].id_equipo
            ))

        # 3. Entrenamientos y Asistencias
        profe_carlos = personal_db["Prof. Carlos Méndez"]
        entrenam_sub11 = Entrenamiento.query.filter_by(id_equipo=equipos_db["Tigres Sub-11"].id_equipo).first()
        if not entrenam_sub11:
            entrenam_sub11 = Entrenamiento(
                dia_semana=1,  # Martes
                hora_inicio=dtime(16, 0),
                hora_fin=dtime(17, 30),
                id_categoria=categorias_db["11"].id_categoria,
                id_equipo=equipos_db["Tigres Sub-11"].id_equipo,
                id_entrenador=profe_carlos.id_personal,
                lugar="Cancha Principal - Césped Natural",
                activo=True
            )
            db.session.add(entrenam_sub11)
            db.session.flush()

            # Sesión pasada con asistencia tomada
            sesion_pasada = SesionEntrenamiento(
                id_entrenamiento=entrenam_sub11.id_entrenamiento,
                fecha=hoy - timedelta(days=7),
                estado="Realizada",
                observacion="Trabajo de posesión de balón y definición"
            )
            db.session.add(sesion_pasada)
            db.session.flush()

            # Asistencias de los alumnos
            asist_data = [
                (alumnos_creados["al_dia_sub11"], "Presente", None),
                (alumnos_creados["proximo_vencer_3d"], "Presente", None),
                (alumnos_creados["beca_100_social"], "Justificado", "Permiso médico por dolor de garganta"),
                (alumnos_creados["beca_25_convenio"], "Tarde", "Retraso de 15 minutos por tráfico"),
            ]
            for alu_obj, est_asist, justif in asist_data:
                db.session.add(AsistenciaEntrenamiento(
                    id_sesion_entrenamiento=sesion_pasada.id_sesion_entrenamiento,
                    id_alumno=alu_obj.id_alumno,
                    estado=est_asist,
                    justificacion=justif
                ))

            # Sesión futura programada
            db.session.add(SesionEntrenamiento(
                id_entrenamiento=entrenam_sub11.id_entrenamiento,
                fecha=hoy + timedelta(days=2),
                estado="Programada",
                observacion="Práctica táctica preparatoria para el partido de fin de semana"
            ))

        # Registrar evento de auditoría general
        db.session.add(Auditoria(
            modulo="Sistema",
            accion="SIEMBRA_COMPLETA_DEMO",
            entidad="BaseDeDatos",
            detalle="Carga exhaustiva de todos los módulos y escenarios deportivos, administrativos y contables."
        ))

        db.session.commit()
        print("\n" + "=" * 80)
        print("¡SIEMBRA MAESTRA COMPLETADA CON ÉXITO!")
        print("=" * 80)
        print(f"Total Alumnos en BD: {Alumno.query.count()}")
        print(f"Total Pagos en BD: {Pago.query.count()}")
        print(f"Total Usuarios: {Usuario.query.count()}")
        print(f"Total Roles: {Rol.query.count()}")
        print(f"Total Partidos: {Partido.query.count()}")
        print(f"Total Ventas: {Venta.query.count()}")
        print(f"Total Compras: {Compra.query.count()}")
        print(f"Total Proveedores: {Proveedor.query.count()}")
        print(f"Total Productos: {Producto.query.count()}")
        print(f"Total Variantes: {ProductoVariante.query.count()}")
        print(f"Total Campeonatos: {Campeonato.query.count()}")
        print("=" * 80)


if __name__ == "__main__":
    try:
        sembrar_todos_los_escenarios()
    except Exception as e:
        print(f"\n[ERROR FATAL]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
