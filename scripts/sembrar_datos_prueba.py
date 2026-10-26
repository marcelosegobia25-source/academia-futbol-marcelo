#!/usr/bin/env python3
"""Sembrador de 10 Alumnos y Flujos Completos de Demostración.

Inserta 10 alumnos con:
- Categorías y equipos reales
- Fichas deportivas completas (posiciones, turnos, medidas, piernas)
- Tutores y relaciones familiares formales
- Inscripciones activas para la gestión 2026
- Obligaciones de mensualidad (7 pagadas en efectivo/QR, 2 pendientes de cobro, 1 con beca 50%)
- Arqueo y sesión de caja con movimientos enlazados
- Entrenamientos programados en agenda y sesión con asistencias (presente, ausente, justificado)
- Torneo de demostración con partido y tabla de posiciones
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
    Usuario, Categoria, Equipo, Alumno, Tutor, AlumnoTutor,
    InscripcionGestion, Obligacion, Pago, AplicacionPago,
    Tarifa, BecaHistorial, SesionCaja, MovimientoContable,
    Lugar, PersonalDeportivo, Entrenamiento, SesionEntrenamiento,
    AsistenciaEntrenamiento, Campeonato, Partido, Posicion, Auditoria
)


def sembrar():
    print("=" * 80)
    print("SEMBRADOR DE DATOS DE PRUEBA: 10 ALUMNOS Y FLUJOS INTEGRALES")
    print("=" * 80)

    app = create_app()
    with app.app_context():
        admin = Usuario.query.filter_by(nombre_usuario="admin").first()
        id_admin = admin.id_usuario if admin else 1

        # ----------------------------------------------------------------------
        # 1. Lugares y Canchas
        # ----------------------------------------------------------------------
        cancha_ppal = Lugar.query.filter_by(nombre="Cancha Principal - Césped").first()
        if not cancha_ppal:
            cancha_ppal = Lugar(
                nombre="Cancha Principal - Césped",
                tipo="Cancha",
                direccion="Av. Costanera N° 450",
                activo=True
            )
            db.session.add(cancha_ppal)
            db.session.flush()

        # ----------------------------------------------------------------------
        # 2. Personal Deportivo (Entrenador)
        # ----------------------------------------------------------------------
        profe = PersonalDeportivo.query.filter_by(documento="7894561").first()
        if not profe:
            profe = PersonalDeportivo(
                nombre="Prof. Carlos Méndez",
                documento="7894561",
                telefono="71234567",
                correo="profe.carlos@academia.com",
                tipo="Entrenador",
                especialidad="Fútbol Formativo",
                fecha_ingreso=date(2025, 1, 15),
                activo=True
            )
            db.session.add(profe)
            db.session.flush()

        # ----------------------------------------------------------------------
        # 3. Categorías y Equipos
        # ----------------------------------------------------------------------
        cat_map = {c.nombre: c for c in Categoria.query.all()}
        
        equipos_data = [
            ("Tigres Sub-9", cat_map.get("9")),
            ("Halcones Sub-11", cat_map.get("11")),
            ("Leones Sub-13", cat_map.get("13")),
            ("Fuerza Sub-15", cat_map.get("15")),
        ]
        equipo_map = {}
        for nombre_eq, cat_obj in equipos_data:
            eq = Equipo.query.filter_by(nombre=nombre_eq).first()
            if not eq:
                eq = Equipo(
                    nombre=nombre_eq,
                    id_categoria=cat_obj.id_categoria if cat_obj else None,
                    es_rival=False
                )
                db.session.add(eq)
                db.session.flush()
            equipo_map[nombre_eq] = eq

        # Equipo rival para partidos de demostración
        eq_rival = Equipo.query.filter_by(nombre="Rival Verde").first()
        if not eq_rival:
            eq_rival = Equipo(
                nombre="Rival Verde",
                id_categoria=cat_map["9"].id_categoria if "9" in cat_map else None,
                es_rival=True
            )
            db.session.add(eq_rival)
            db.session.flush()

        # Tarifa mensual estándar
        tarifa_gral = Tarifa.query.filter_by(concepto="Mensualidad General").first()
        if not tarifa_gral:
            tarifa_gral = Tarifa(
                concepto="Mensualidad General",
                monto=Decimal("150.00"),
                fecha_inicio=date(2026, 1, 1),
                activo=True
            )
            db.session.add(tarifa_gral)
            db.session.flush()

        # ----------------------------------------------------------------------
        # 4. Datos de los 10 Alumnos y sus Familias
        # ----------------------------------------------------------------------
        datos_alumnos = [
            {
                "ci": "10982341", "nombre": "Mateo", "apellido": "Fernández Ramos",
                "nac": date(2017, 4, 12), "cat": "9", "equipo": "Tigres Sub-9",
                "pos": "DEL", "pie": "Derecha", "peso": 31.5, "est": 1.34, "sexo": "M",
                "turno": "Mañana", "estado": "Activo", "beca": "Ninguna",
                "tutor_nom": "Jorge Fernández", "tutor_doc": "4589210", "tutor_tel": "76543210",
                "parentesco": "Padre", "pago": "Efectivo", "monto_pago": Decimal("150.00"), "nro_op": "EF-1001"
            },
            {
                "ci": "11234567", "nombre": "Sofía", "apellido": "Quispe Morales",
                "nac": date(2015, 8, 20), "cat": "11", "equipo": "Halcones Sub-11",
                "pos": "MED", "pie": "Izquierda", "peso": 37.0, "est": 1.42, "sexo": "F",
                "turno": "Tarde", "estado": "Activo", "beca": "Ninguna",
                "tutor_nom": "Carmen Morales", "tutor_doc": "5678901", "tutor_tel": "78901234",
                "parentesco": "Madre", "pago": "QR", "monto_pago": Decimal("150.00"), "nro_op": "QR-882314"
            },
            {
                "ci": "12345678", "nombre": "Santiago", "apellido": "Torrico López",
                "nac": date(2019, 2, 15), "cat": "7", "equipo": None,
                "pos": "DEF", "pie": "Derecha", "peso": 24.0, "est": 1.22, "sexo": "M",
                "turno": "Mañana", "estado": "Activo", "beca": "Ninguna",
                "tutor_nom": "Raúl Torrico", "tutor_doc": "3456789", "tutor_tel": "70123456",
                "parentesco": "Padre", "pago": "Efectivo", "monto_pago": Decimal("150.00"), "nro_op": "EF-1002"
            },
            {
                "ci": "13456789", "nombre": "Camila", "apellido": "Villarroel Flores",
                "nac": date(2013, 11, 5), "cat": "13", "equipo": "Leones Sub-13",
                "pos": "DEL", "pie": "Derecha", "peso": 44.5, "est": 1.52, "sexo": "F",
                "turno": "Tarde", "estado": "Activo", "beca": "Media",
                "tutor_nom": "Patricia Flores", "tutor_doc": "4567890", "tutor_tel": "71234567",
                "parentesco": "Madre", "pago": "QR", "monto_pago": Decimal("75.00"), "nro_op": "QR-901234", "porc_beca": 50
            },
            {
                "ci": "14567890", "nombre": "Nicolás", "apellido": "Arze Mendoza",
                "nac": date(2011, 6, 30), "cat": "15", "equipo": "Fuerza Sub-15",
                "pos": "POR", "pie": "Derecha", "peso": 58.0, "est": 1.70, "sexo": "M",
                "turno": "Mañana", "estado": "Activo", "beca": "Ninguna",
                "tutor_nom": "Fernando Arze", "tutor_doc": "2345678", "tutor_tel": "72345678",
                "parentesco": "Padre", "pago": "Efectivo", "monto_pago": Decimal("150.00"), "nro_op": "EF-1003"
            },
            {
                "ci": "15678901", "nombre": "Luciana", "apellido": "Rojas Céspedes",
                "nac": date(2017, 9, 18), "cat": "9", "equipo": "Tigres Sub-9",
                "pos": "MED", "pie": "Ambas", "peso": 30.0, "est": 1.32, "sexo": "F",
                "turno": "Mañana", "estado": "Activo", "beca": "Ninguna",
                "tutor_nom": "Elena Céspedes", "tutor_doc": "3456781", "tutor_tel": "73456789",
                "parentesco": "Madre", "pago": None, "monto_pago": None, "nro_op": None
            },
            {
                "ci": "16789012", "nombre": "Gabriel", "apellido": "Mamani Cruz",
                "nac": date(2015, 3, 25), "cat": "11", "equipo": "Halcones Sub-11",
                "pos": "DEF", "pie": "Izquierda", "peso": 38.5, "est": 1.45, "sexo": "M",
                "turno": "Tarde", "estado": "Activo", "beca": "Ninguna",
                "tutor_nom": "Mario Mamani", "tutor_doc": "4567892", "tutor_tel": "74567890",
                "parentesco": "Padre", "pago": "QR", "monto_pago": Decimal("150.00"), "nro_op": "QR-778899"
            },
            {
                "ci": "17890123", "nombre": "Sebastián", "apellido": "Gutiérrez Prado",
                "nac": date(2013, 5, 14), "cat": "13", "equipo": "Leones Sub-13",
                "pos": "MED", "pie": "Derecha", "peso": 46.0, "est": 1.55, "sexo": "M",
                "turno": "Mañana", "estado": "Activo", "beca": "Ninguna",
                "tutor_nom": "Andrea Prado", "tutor_doc": "5678903", "tutor_tel": "75678901",
                "parentesco": "Madre", "pago": None, "monto_pago": None, "nro_op": None
            },
            {
                "ci": "18901234", "nombre": "Valeria", "apellido": "Pinto Sánchez",
                "nac": date(2019, 10, 10), "cat": "7", "equipo": None,
                "pos": "DEL", "pie": "Derecha", "peso": 23.5, "est": 1.20, "sexo": "F",
                "turno": "Tarde", "estado": "Activo", "beca": "Ninguna",
                "tutor_nom": "Carlos Pinto", "tutor_doc": "6789014", "tutor_tel": "76789012",
                "parentesco": "Padre", "pago": "Efectivo", "monto_pago": Decimal("150.00"), "nro_op": "EF-1004"
            },
            {
                "ci": "19012345", "nombre": "Matías", "apellido": "Suárez Vargas",
                "nac": date(2011, 1, 22), "cat": "15", "equipo": "Fuerza Sub-15",
                "pos": "DEF", "pie": "Derecha", "peso": 56.0, "est": 1.68, "sexo": "M",
                "turno": "Mañana", "estado": "Retirado", "beca": "Ninguna",
                "tutor_nom": "Silvia Vargas", "tutor_doc": "7890125", "tutor_tel": "77890123",
                "parentesco": "Madre", "pago": None, "monto_pago": None, "nro_op": None
            },
        ]

        # ----------------------------------------------------------------------
        # 5. Sesión de Caja Activa
        # ----------------------------------------------------------------------
        sesion = SesionCaja.query.filter_by(estado="Abierta").order_by(SesionCaja.id_sesion.desc()).first()
        if not sesion:
            sesion = SesionCaja(
                id_usuario=id_admin,
                saldo_inicial=Decimal("200.00"),
                estado="Abierta",
                observacion="Apertura formal de caja - Turno General"
            )
            db.session.add(sesion)
            db.session.flush()

        periodo_actual = "2026-10"
        hoy = date.today()
        vencimiento = hoy + timedelta(days=25)

        alumnos_creados = []
        pagos_creados = 0

        for item in datos_alumnos:
            # Buscar o crear Alumno
            al = Alumno.query.filter_by(ci=item["ci"]).first()
            cat_obj = cat_map.get(item["cat"])
            eq_obj = equipo_map.get(item["equipo"]) if item["equipo"] else None

            if not al:
                al = Alumno(
                    nombre=item["nombre"],
                    apellido=item["apellido"],
                    ci=item["ci"],
                    fecha_nacimiento=item["nac"],
                    id_categoria=cat_obj.id_categoria if cat_obj else None,
                    posicion=item["pos"],
                    pierna_habil=item["pie"],
                    peso=item["peso"],
                    estatura=item["est"],
                    sexo=item["sexo"],
                    turno=item["turno"],
                    estado=item["estado"],
                    beca=item["beca"],
                    tutor=item["tutor_nom"],
                    telefono=item["tutor_tel"],
                    direccion="Zona Central, Calle Los Álamos",
                    fecha_base_pago=hoy
                )
                if eq_obj and eq_obj not in al.equipos:
                    al.equipos.append(eq_obj)
                db.session.add(al)
                db.session.flush()
                print(f"  + Alumno creado: {al.nombre} {al.apellido} ({al.posicion}, Cat Sub-{item['cat']})")
            else:
                if eq_obj and eq_obj not in al.equipos:
                    al.equipos.append(eq_obj)
                print(f"  * Alumno ya existía: {al.nombre} {al.apellido}")
            
            alumnos_creados.append(al)

            # Buscar o crear Tutor
            tut = Tutor.query.filter_by(documento=item["tutor_doc"]).first()
            if not tut:
                tut = Tutor(
                    nombre=item["tutor_nom"],
                    documento=item["tutor_doc"],
                    telefono=item["tutor_tel"],
                    correo=f"{item['nombre'].lower()}.familia@ejemplo.com",
                    direccion="Zona Central, Calle Los Álamos",
                    activo=True
                )
                db.session.add(tut)
                db.session.flush()
            
            # Relación Alumno - Tutor
            rel_tut = AlumnoTutor.query.filter_by(id_alumno=al.id_alumno, id_tutor=tut.id_tutor).first()
            if not rel_tut:
                rel_tut = AlumnoTutor(
                    id_alumno=al.id_alumno,
                    id_tutor=tut.id_tutor,
                    parentesco=item["parentesco"],
                    principal=True,
                    autorizado_recoger=True
                )
                db.session.add(rel_tut)

            # Inscripción formal a la gestión 2026
            insc = InscripcionGestion.query.filter_by(id_alumno=al.id_alumno, gestion=2026).first()
            if not insc:
                insc = InscripcionGestion(
                    id_alumno=al.id_alumno,
                    gestion=2026,
                    fecha_inscripcion=hoy - timedelta(days=60),
                    estado="Activa" if item["estado"] == "Activo" else "Retirada",
                    id_categoria=cat_obj.id_categoria if cat_obj else None,
                    id_equipo_principal=eq_obj.id_equipo if eq_obj else None,
                    id_tarifa=tarifa_gral.id_tarifa,
                    monto_tarifa=Decimal("150.00"),
                    porcentaje_beca=Decimal(item.get("porc_beca", 0)),
                    observacion="Inscripción anual regular"
                )
                db.session.add(insc)

            # Historial de Beca si aplica
            if item["beca"] == "Media":
                beca_reg = BecaHistorial.query.filter_by(id_alumno=al.id_alumno).first()
                if not beca_reg:
                    beca_reg = BecaHistorial(
                        id_alumno=al.id_alumno,
                        porcentaje=Decimal("50.00"),
                        fecha_inicio=hoy - timedelta(days=30),
                        fecha_fin=hoy + timedelta(days=330),
                        motivo="Beca por Mérito Deportivo / Rendimiento",
                        autorizado_por="Comité Deportivo",
                        estado="Activa",
                        id_usuario=id_admin
                    )
                    db.session.add(beca_reg)

            # Obligación de Mensualidad
            ob = Obligacion.query.filter_by(
                id_alumno=al.id_alumno,
                concepto="Mensualidad",
                periodo=periodo_actual
            ).first()
            if not ob:
                monto_orig = Decimal("150.00")
                descuento = Decimal("75.00") if item["beca"] == "Media" else Decimal("0.00")
                ob = Obligacion(
                    id_alumno=al.id_alumno,
                    concepto="Mensualidad",
                    periodo=periodo_actual,
                    monto_original=monto_orig,
                    descuento=descuento,
                    recargo=Decimal("0.00"),
                    cubierto_beca=False,
                    fecha_vencimiento=vencimiento
                )
                db.session.add(ob)
                db.session.flush()

            # Registrar Pago si corresponde
            if item["pago"] and item["monto_pago"]:
                pago_existente = Pago.query.filter_by(
                    id_alumno=al.id_alumno,
                    mes_pagado=periodo_actual
                ).first()
                if not pago_existente:
                    pago_nuevo = Pago(
                        id_alumno=al.id_alumno,
                        fecha_pago=hoy - timedelta(days=2),
                        fecha_vencimiento=vencimiento,
                        mes_pagado=periodo_actual,
                        modo_pago=item["pago"],
                        monto=item["monto_pago"],
                        numero_operacion=item["nro_op"],
                        es_beca=(item["beca"] != "Ninguna")
                    )
                    db.session.add(pago_nuevo)
                    db.session.flush()

                    # Vincular pago con obligación
                    ap = AplicacionPago(
                        id_obligacion=ob.id_obligacion,
                        id_pago=pago_nuevo.id_pago,
                        monto=item["monto_pago"]
                    )
                    db.session.add(ap)

                    # Registrar movimiento contable (esto dispara la creación de movimiento_caja si id_sesion_caja está presente)
                    mov_cont = MovimientoContable.query.filter_by(
                        origen_tipo="Pago", origen_id=pago_nuevo.id_pago
                    ).first()
                    if not mov_cont:
                        mov_cont = MovimientoContable(
                            id_sesion_caja=sesion.id_sesion,
                            tipo="Ingreso",
                            categoria="Mensualidades",
                            concepto=f"Pago mensualidad {periodo_actual} - {al.nombre_completo}",
                            monto=item["monto_pago"],
                            fecha=hoy - timedelta(days=2),
                            modo_pago=item["pago"],
                            numero_operacion=item["nro_op"],
                            origen_tipo="Pago",
                            origen_id=pago_nuevo.id_pago,
                        )
                        db.session.add(mov_cont)
                    pagos_creados += 1

        db.session.flush()

        # ----------------------------------------------------------------------
        # 6. Entrenamientos y Asistencias de Muestra
        # ----------------------------------------------------------------------
        ent_sub9 = Entrenamiento.query.filter_by(id_categoria=cat_map["9"].id_categoria).first()
        if not ent_sub9:
            ent_sub9 = Entrenamiento(
                id_categoria=cat_map["9"].id_categoria,
                id_entrenador=profe.id_personal,
                id_lugar=cancha_ppal.id_lugar,
                dia_semana=2,  # Miércoles
                hora_inicio=dtime(16, 0),
                hora_fin=dtime(17, 30),
                activo=True
            )
            db.session.add(ent_sub9)
            db.session.flush()

        # Sesión de entrenamiento reciente
        fecha_sesion = hoy - timedelta(days=1)
        sesion_ent = SesionEntrenamiento.query.filter_by(
            id_entrenamiento=ent_sub9.id_entrenamiento,
            fecha=fecha_sesion
        ).first()
        if not sesion_ent:
            sesion_ent = SesionEntrenamiento(
                id_entrenamiento=ent_sub9.id_entrenamiento,
                fecha=fecha_sesion,
                estado="Realizada",
                observacion="Trabajo de pase, recepción y definición"
            )
            db.session.add(sesion_ent)
            db.session.flush()

        # Marcar asistencias para alumnos de la categoría Sub-9
        for al in alumnos_creados:
            if al.id_categoria == cat_map["9"].id_categoria:
                asis = AsistenciaEntrenamiento.query.filter_by(
                    id_sesion_entrenamiento=sesion_ent.id_sesion_entrenamiento,
                    id_alumno=al.id_alumno
                ).first()
                if not asis:
                    asis = AsistenciaEntrenamiento(
                        id_sesion_entrenamiento=sesion_ent.id_sesion_entrenamiento,
                        id_alumno=al.id_alumno,
                        estado="Presente"
                    )
                    db.session.add(asis)

        # ----------------------------------------------------------------------
        # 7. Campeonato, Partido y Tabla de Posiciones
        # ----------------------------------------------------------------------
        camp = Campeonato.query.filter_by(nombre="Copa Apertura 2026").first()
        if not camp:
            camp = Campeonato(
                nombre="Copa Apertura 2026",
                fecha_inicio=hoy - timedelta(days=15),
                fecha_fin=hoy + timedelta(days=60),
                formato="Liga",
                estado="En curso"
            )
            if "9" in cat_map and cat_map["9"] not in camp.categorias:
                camp.categorias.append(cat_map["9"])
            db.session.add(camp)
            db.session.flush()

        # Inscribir equipos
        eq1 = equipo_map.get("Tigres Sub-9")
        if eq1 and eq1 not in camp.equipos:
            camp.equipos.append(eq1)
        if eq_rival and eq_rival not in camp.equipos:
            camp.equipos.append(eq_rival)
        db.session.flush()

        if eq1 and eq_rival:
            # Partido jugado
            partido = Partido.query.filter_by(
                id_campeonato=camp.id_campeonato,
                id_equipo=eq1.id_equipo,
                id_equipo_rival=eq_rival.id_equipo
            ).first()
            if not partido:
                partido = Partido(
                    id_campeonato=camp.id_campeonato,
                    id_equipo=eq1.id_equipo,
                    id_equipo_rival=eq_rival.id_equipo,
                    rival=eq_rival.nombre,
                    id_categoria=cat_map["9"].id_categoria,
                    fecha=hoy - timedelta(days=5),
                    hora=dtime(10, 0),
                    id_lugar=cancha_ppal.id_lugar,
                    cancha=cancha_ppal.nombre,
                    goles_local=3,
                    goles_visita=1,
                    resultado="3 - 1",
                    estado_partido="Finalizado",
                    fase="Liga",
                    jornada=1
                )
                db.session.add(partido)
                db.session.flush()

            # Tabla de posiciones
            pos1 = Posicion.query.filter_by(
                id_campeonato=camp.id_campeonato,
                id_categoria=cat_map["9"].id_categoria,
                id_equipo=eq1.id_equipo
            ).first()
            if not pos1:
                db.session.add(Posicion(
                    id_campeonato=camp.id_campeonato,
                    id_categoria=cat_map["9"].id_categoria,
                    id_equipo=eq1.id_equipo,
                    pj=1, pg=1, pe=0, pp=0,
                    gf=3, gc=1
                ))

            pos2 = Posicion.query.filter_by(
                id_campeonato=camp.id_campeonato,
                id_categoria=cat_map["9"].id_categoria,
                id_equipo=eq_rival.id_equipo
            ).first()
            if not pos2:
                db.session.add(Posicion(
                    id_campeonato=camp.id_campeonato,
                    id_categoria=cat_map["9"].id_categoria,
                    id_equipo=eq_rival.id_equipo,
                    pj=1, pg=0, pe=0, pp=1,
                    gf=1, gc=3
                ))

        # Registrar en auditoría
        db.session.add(Auditoria(
            modulo="Sistema",
            accion="Sembrado de datos de prueba",
            entidad="Demostración",
            id_entidad=1,
            id_usuario=id_admin,
            detalle="Carga exitosa de 10 alumnos, tutores, pagos, caja, entrenamientos y torneo"
        ))

        db.session.commit()

        print("\n" + "=" * 80)
        print("SEMBRADO COMPLETADO CON EXITO EN SUPABASE")
        print(f"   * Alumnos registrados: {len(alumnos_creados)}")
        print(f"   * Mensualidades cobradas: {pagos_creados} (Efectivo y QR)")
        print(f"   * Mensualidades pendientes para auditoria: 2")
        print(f"   * Becas activas configuradas: 1 (50% Media Beca)")
        print(f"   * Equipos configurados: {len(equipo_map)}")
        print(f"   * Sesion de caja activa y movimientos registrados")
        print(f"   * Asistencia de entrenamiento y torneo registrados")
        print("=" * 80)


if __name__ == "__main__":
    sembrar()
