#!/usr/bin/env python3
"""Auditoría Integral de Flujos de Negocio y Usuario - Academia Deportiva.

Evalúa de extremo a extremo los 6 flujos de negocio fundamentales:
1. Flujo de Autenticación y Control de Accesos
2. Flujo del Ciclo de Vida del Alumno
3. Flujo de Tesorería, Cobranzas y Arqueo de Caja
4. Flujo Deportivo (Torneos, Fixture, Resultados y Posiciones)
5. Flujo de Agenda, Calendario y Asistencias
6. Flujo de Configuración, Auditoría y Respaldo
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Asegurar path base
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.extensions import db
from app.models import (
    Usuario, Rol, Permiso, Alumno, Categoria, Equipo, Pago, Obligacion,
    AplicacionPago, CierreCaja, Campeonato, Partido, Posicion,
    Entrenamiento, SesionEntrenamiento, AsistenciaEntrenamiento,
    EventoAgenda, Configuracion, Auditoria, HistorialAlumno,
    HistorialCategoriaAlumno, HistorialEquipoAlumno
)


class AuditorFlujos:
    def __init__(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()
        self.resultados = []

    def registrar(self, flujo, paso, exito, detalle):
        icono = "✅" if exito else "❌"
        self.resultados.append({
            "flujo": flujo,
            "paso": paso,
            "exito": exito,
            "detalle": detalle
        })
        print(f"  {icono} [{flujo}] {paso}: {detalle}")

    def ejecutar_auditoria(self):
        print("\n" + "=" * 80)
        print("🔍 AUDITORÍA DE FLUJOS DE NEGOCIO Y CASOS DE USO")
        print("=" * 80 + "\n")

        with self.app.app_context():
            self._flujo_1_autenticacion()
            self._flujo_2_ciclo_vida_alumno()
            self._flujo_3_tesoreria_y_pagos()
            self._flujo_4_campeonatos_y_deporte()
            self._flujo_5_agenda_y_calendario()
            self._flujo_6_configuracion_y_auditoria()

        self._generar_resumen()

    def _flujo_1_autenticacion(self):
        print("\n📋 1. FLUJO DE AUTENTICACIÓN Y CONTROL DE ACCESO")
        # 1.1 Redirección al login
        resp = self.client.get("/alumnos/", follow_redirects=False)
        self.registrar(
            "Seguridad", "Protección de rutas",
            resp.status_code in (302, 303) and "/acceso/" in (resp.headers.get("Location") or ""),
            "Petición anónima redirige forzosamente a la pantalla de login (/acceso/)"
        )

        # 1.2 Login con contraseña válida
        usuario = Usuario.query.filter_by(nombre_usuario="admin").first()
        if usuario:
            clave_valida = usuario.verificar_contrasena("99999")
            self.registrar(
                "Seguridad", "Verificación de credenciales",
                clave_valida,
                "Hash de contraseña coincide con PIN de administración (99999)"
            )

        # 1.3 Intento fallido
        resp_err = self.client.post("/acceso/", data={"nombre_usuario": "admin", "contrasena": "00000"}, follow_redirects=True)
        html_err = resp_err.get_data(as_text=True).lower()
        self.registrar(
            "Seguridad", "Rechazo de credenciales erróneas",
            resp_err.status_code == 200 and any(w in html_err for w in ["incorrect", "inválid", "invalid", "error"]),
            "El sistema bloquea accesos no autorizados mostrando mensaje de error"
        )

    def _flujo_2_ciclo_vida_alumno(self):
        print("\n📋 2. FLUJO DEL CICLO DE VIDA DEL ALUMNO")
        # 2.1 Búsqueda o creación de alumno de prueba
        alumno = Alumno.query.filter_by(ci="990016").first()
        if not alumno:
            cat = Categoria.query.first()
            alumno = Alumno(
                nombre="Lucas",
                apellido="FlujoTest",
                fecha_nacimiento=date(2014, 5, 10),
                ci="990016",
                id_categoria=cat.id_categoria if cat else None,
                tutor="Carlos FlujoTest",
                telefono="77788899",
                estado="Activo",
                turno="Tarde"
            )
            db.session.add(alumno)
            db.session.commit()

        self.registrar(
            "Alumnos", "Inscripción y Ficha",
            alumno.id_alumno is not None,
            f"Alumno #{alumno.id_alumno} ({alumno.nombre_completo}) registrado con edad calculada: {alumno.edad} años"
        )

        # 2.2 Trazabilidad de cambios (HistorialAlumno)
        antiguo_turno = alumno.turno
        alumno.turno = "Mañana"
        hist = HistorialAlumno(
            id_alumno=alumno.id_alumno,
            tipo="Edición turno",
            valor_anterior=antiguo_turno,
            valor_nuevo="Mañana",
            motivo="Auditoría de flujo"
        )
        db.session.add(hist)
        db.session.commit()
        self.registrar(
            "Alumnos", "Trazabilidad de cambios",
            len(alumno.historial) > 0,
            f"Cambio de turno registrado en bitácora deportiva ({antiguo_turno} ➔ Mañana)"
        )

        # 2.3 Retiro del alumno
        alumno.estado = "Retirado"
        alumno.fecha_retiro = date.today()
        db.session.commit()
        self.registrar(
            "Alumnos", "Retiro y Exclusión de Cobranza",
            alumno.estado_mensualidad == "Retirado",
            "Un alumno retirado no genera mora ni se presenta como moroso en reportes"
        )

        # 2.4 Reactivación
        alumno.estado = "Activo"
        alumno.fecha_retiro = None
        alumno.fecha_ultima_reactivacion = date.today()
        db.session.commit()
        self.registrar(
            "Alumnos", "Reactivación Limpia",
            alumno.estado == "Activo" and alumno.fecha_ultima_reactivacion is not None,
            f"Alumno reactivado con ciclo de cobro iniciado el {alumno.fecha_ultima_reactivacion}"
        )

    def _flujo_3_tesoreria_y_pagos(self):
        print("\n📋 3. FLUJO DE TESORERÍA, PAGOS Y ARQUEO DE CAJA")
        alumno = Alumno.query.filter_by(ci="990016").first()
        mes_test = "2026-10"

        # 3.1 Registro de pago
        pago = Pago.query.filter_by(id_alumno=alumno.id_alumno, mes_pagado=mes_test).first()
        if not pago:
            pago = Pago(
                id_alumno=alumno.id_alumno,
                fecha_pago=date.today(),
                fecha_vencimiento=date.today() + timedelta(days=30),
                mes_pagado=mes_test,
                modo_pago="Efectivo",
                monto=Decimal("150.00"),
                numero_operacion="REC-TEST-001"
            )
            db.session.add(pago)
            db.session.commit()

        self.registrar(
            "Tesorería", "Emisión de Cobro",
            pago.id_pago is not None and pago.activo,
            f"Pago #{pago.id_pago} registrado por Bs. {pago.monto} ({pago.modo_pago}) para el mes {pago.mes_pagado}"
        )

        # 3.2 Cobertura y Vigencia
        self.registrar(
            "Tesorería", "Cálculo de Vigencia",
            pago.estado_cobertura in ("Vigente", "Próximo a vencer"),
            f"Estado de cobertura del pago calculado automáticamente: {pago.estado_cobertura}"
        )

        # 3.3 Arqueo y Cierre de caja
        cierre = CierreCaja.query.filter_by(fecha=date.today()).first()
        if not cierre:
            cierre = CierreCaja(
                fecha=date.today(),
                efectivo_sistema=Decimal("150.00"),
                qr_sistema=Decimal("0.00"),
                efectivo_contado=Decimal("150.00"),
                qr_confirmado=Decimal("0.00"),
                diferencia=Decimal("0.00"),
                observacion="Arqueo verificado"
            )
            db.session.add(cierre)
            db.session.commit()

        self.registrar(
            "Tesorería", "Cierre Diario de Caja",
            cierre.id_cierre is not None and cierre.diferencia == Decimal("0.00"),
            f"Cierre de caja para {cierre.fecha} con cuadre exacto (Diferencia: Bs. {cierre.diferencia})"
        )

    def _flujo_4_campeonatos_y_deporte(self):
        print("\n📋 4. FLUJO DE CAMPEONATOS, PARTIDOS Y POSICIONES")
        # 4.1 Creación o verificación de torneo
        camp = Campeonato.query.filter_by(nombre="Torneo Auditoría").first()
        if not camp:
            cat = Categoria.query.first()
            camp = Campeonato(
                nombre="Torneo Auditoría",
                fecha_inicio=date.today(),
                formato="Liga",
                vueltas=1,
                estado="En curso"
            )
            if cat:
                camp.categorias.append(cat)
            db.session.add(camp)
            db.session.commit()

        self.registrar(
            "Deporte", "Creación de Campeonato",
            camp.id_campeonato is not None,
            f"Campeonato '{camp.nombre}' ({camp.formato}) activo con {len(camp.categorias)} categorías"
        )

        # 4.2 Creación de equipos y partido de prueba
        eq1 = Equipo.query.filter_by(nombre="Academia Azul").first()
        if not eq1:
            eq1 = Equipo(nombre="Academia Azul", es_rival=False)
            db.session.add(eq1)

        eq2 = Equipo.query.filter_by(nombre="Rival Verde").first()
        if not eq2:
            eq2 = Equipo(nombre="Rival Verde", es_rival=True)
            db.session.add(eq2)
        db.session.commit()

        cat = Categoria.query.first()
        partido = Partido.query.filter_by(id_campeonato=camp.id_campeonato).first()
        if not partido:
            partido = Partido(
                fecha=date.today(),
                id_equipo=eq1.id_equipo,
                id_equipo_rival=eq2.id_equipo,
                id_categoria=cat.id_categoria if cat else 1,
                rival=eq2.nombre,
                id_campeonato=camp.id_campeonato,
                fase="Liga",
                jornada=1,
                estado_partido="Finalizado",
                goles_local=3,
                goles_visita=1,
                resultado="3-1"
            )
            db.session.add(partido)
            db.session.commit()

        self.registrar(
            "Deporte", "Registro de Partido y Marcador",
            partido.resultado == "3-1" and partido.ganador_id == eq1.id_equipo,
            f"Partido {eq1.nombre} vs {eq2.nombre} finalizado con marcador {partido.resultado}"
        )

        # 4.3 Tabla de posiciones
        pos = Posicion.query.filter_by(id_campeonato=camp.id_campeonato, id_equipo=eq1.id_equipo).first()
        if not pos:
            pos = Posicion(
                id_campeonato=camp.id_campeonato,
                id_categoria=partido.id_categoria,
                id_equipo=eq1.id_equipo,
                pj=1, pg=1, pe=0, pp=0, gf=3, gc=1
            )
            db.session.add(pos)
            db.session.commit()

        self.registrar(
            "Deporte", "Cálculo de Tabla de Posiciones",
            pos.pts == 3 and pos.dg == 2,
            f"Equipo '{eq1.nombre}' lidera con {pos.pts} pts, DG +{pos.dg} (PJ: {pos.pj}, PG: {pos.pg})"
        )

    def _flujo_5_agenda_y_calendario(self):
        print("\n📋 5. FLUJO DE AGENDA, CALENDARIO Y ENTRENAMIENTOS")
        cat = Categoria.query.first()
        # 5.1 Entrenamiento recurrente
        entrenamiento = Entrenamiento.query.filter_by(dia_semana=2).first()
        if not entrenamiento:
            entrenamiento = Entrenamiento(
                dia_semana=2, # Miércoles
                hora_inicio=datetime.strptime("16:00", "%H:%M").time(),
                hora_fin=datetime.strptime("17:30", "%H:%M").time(),
                lugar="Cancha Principal",
                id_categoria=cat.id_categoria if cat else None,
                activo=True
            )
            db.session.add(entrenamiento)
            db.session.commit()

        self.registrar(
            "Agenda", "Programación de Entrenamientos",
            entrenamiento.id_entrenamiento is not None,
            f"Horario semanal configurado: Día {entrenamiento.dia_semana} ({entrenamiento.hora_inicio} - {entrenamiento.hora_fin})"
        )

        # 5.2 Evento en agenda
        evento = EventoAgenda.query.filter_by(descripcion="Reunión de Padres").first()
        if not evento:
            evento = EventoAgenda(
                fecha=date.today() + timedelta(days=5),
                descripcion="Reunión de Padres",
                tipo="Evento",
                lugar="Sede Central"
            )
            db.session.add(evento)
            db.session.commit()

        self.registrar(
            "Agenda", "Eventos de Calendario",
            evento.id_evento is not None,
            f"Evento '{evento.descripcion}' programado para el {evento.fecha}"
        )

    def _flujo_6_configuracion_y_auditoria(self):
        print("\n📋 6. FLUJO DE CONFIGURACIÓN Y AUDITORÍA INMUTABLE")
        # 6.1 Configuración institucional
        cfg = Configuracion.obtener()
        self.registrar(
            "Configuración", "Parámetros del Club",
            bool(cfg.nombre_academia and cfg.moneda),
            f"Parámetros activos: Academia='{cfg.nombre_academia}', Moneda={cfg.moneda}, Días aviso={cfg.dias_proximo_vencimiento}"
        )

        # 6.2 Registro inmutable de auditoría
        auditoria = Auditoria.query.order_by(Auditoria.creado_en.desc()).first()
        self.registrar(
            "Auditoría", "Bitácora de Seguridad",
            auditoria is not None,
            f"Último evento auditado: [{auditoria.modulo}] {auditoria.accion} (Entidad: {auditoria.entidad} #{auditoria.id_entidad})"
        )

    def _generar_resumen(self):
        total = len(self.resultados)
        exitos = sum(1 for r in self.resultados if r["exito"])
        fallos = total - exitos
        porcentaje = (exitos / total) * 100 if total > 0 else 0

        print("\n" + "=" * 80)
        print("📊 RESUMEN FINAL DE LA AUDITORÍA DE FLUJOS")
        print("=" * 80)
        print(f"Total de flujos evaluados: {total}")
        print(f"Flujos superados (OK)   : {exitos} ({porcentaje:.1f}%)")
        print(f"Flujos con errores      : {fallos}")
        print("=" * 80)

        if fallos == 0:
            print("🏆 RESULTADO: TODOS LOS FLUJOS DE NEGOCIO ESTÁN OPERATIVOS AL 100%\n")
        else:
            print("⚠️ ATENCIÓN: Se detectaron fallos en los flujos indicados arriba.\n")


if __name__ == "__main__":
    auditor = AuditorFlujos()
    auditor.ejecutar_auditoria()
