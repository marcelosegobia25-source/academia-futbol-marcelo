"""Carga idempotente de casos de prueba para los módulos añadidos."""
from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.extensions import db
from app.models import (
    Alumno, AlumnoTutor, AplicacionPago, AsistenciaEntrenamiento, Auditoria,
    BecaHistorial, Categoria, CategoriaContable, Compra, ConteoInventario,
    CuotaProgramada, DetalleCompra, DetalleConteoInventario, DetalleDevolucionVenta,
    DetalleVenta, DevolucionVenta, Entrenamiento, Equipo, HistorialCategoriaAlumno,
    HistorialEquipoAlumno, InscripcionGestion, MovimientoContable, MovimientoInventario,
    Obligacion, Pago, PagoProgramado, PersonalDeportivo, Producto, ProductoVariante,
    Proveedor, SesionEntrenamiento, Tarifa, Tutor, Venta,
)

MARCA = "POBLACION_DEMO_MODULOS_V1"


def obtener(modelo, defaults=None, **filtros):
    objeto = modelo.query.filter_by(**filtros).first()
    if objeto:
        return objeto
    objeto = modelo(**filtros, **(defaults or {}))
    db.session.add(objeto); db.session.flush()
    return objeto


def ejecutar():
    if Auditoria.query.filter_by(accion=MARCA).first():
        print("Los datos de demostración ya estaban cargados; no se duplicaron.")
        return
    hoy = date.today()
    categoria = Categoria.query.filter(Categoria.edad_min.isnot(None)).order_by(Categoria.edad_min).first()
    if not categoria:
        raise RuntimeError("Debe existir al menos una categoría deportiva.")
    equipo = Equipo.query.filter_by(es_rival=False, activo=True).first()
    if not equipo:
        equipo = obtener(Equipo, nombre="Equipo demostración", id_categoria=categoria.id_categoria, es_rival=False, activo=True)

    categorias = {}
    for nombre, tipo in (("Mensualidades", "Ingreso"), ("Uniformes", "Ingreso"),
                         ("Alquiler", "Egreso"), ("Pago a profesores", "Egreso"),
                         ("Equipo deportivo", "Egreso"), ("Devoluciones de venta", "Egreso")):
        categorias[nombre] = obtener(CategoriaContable, nombre=nombre, defaults={"tipo": tipo, "activo": True})

    proveedor_uniformes = obtener(Proveedor, nombre="[DEMO] Textiles Deportivos", defaults={
        "tipo_persona": "Empresa", "documento": "NIT-DEMO-01", "telefono": "70000001",
        "correo": "textiles@demo.local", "contacto": "Ana Demostración", "activo": True,
    })
    proveedor_cancha = obtener(Proveedor, nombre="[DEMO] Cancha Central", defaults={
        "tipo_persona": "Empresa", "documento": "NIT-DEMO-02", "telefono": "70000002", "activo": True,
    })

    entrenador = obtener(PersonalDeportivo, nombre="[DEMO] Carlos Entrenador", defaults={
        "documento": "ENT-DEMO-01", "telefono": "71000001", "especialidad": "Fútbol formativo",
        "tipo": "Entrenador", "fecha_ingreso": hoy - timedelta(days=180), "activo": True,
    })
    obtener(PersonalDeportivo, nombre="[DEMO] Laura Preparadora", defaults={
        "documento": "ENT-DEMO-02", "telefono": "71000002", "especialidad": "Preparación física",
        "tipo": "Preparador físico", "fecha_ingreso": hoy - timedelta(days=90), "activo": True,
    })
    retirado = obtener(PersonalDeportivo, nombre="[DEMO] Profesor retirado", defaults={
        "documento": "ENT-DEMO-03", "tipo": "Profesor", "fecha_ingreso": hoy - timedelta(days=400),
        "fecha_salida": hoy - timedelta(days=30), "activo": False,
    })

    tutor = obtener(Tutor, nombre="[DEMO] Familia Caso", defaults={"telefono": "72000001", "correo": "familia@demo.local"})
    alumnos = []
    casos = [
        ("Activo", "Sin deuda", "DEMO-ALU-01", "Ninguna", 0),
        ("Becado", "Completo", "DEMO-ALU-02", "Completa", 100),
        ("Pago", "Parcial", "DEMO-ALU-03", "Ninguna", 0),
        ("Alumno", "Retirado", "DEMO-ALU-04", "Media", 50),
    ]
    for indice, (nombre, apellido, ci, beca, porcentaje) in enumerate(casos):
        alumno = Alumno.query.filter_by(ci=ci).first()
        if not alumno:
            alumno = Alumno(
                nombre=f"[DEMO] {nombre}", apellido=apellido, ci=ci,
                fecha_nacimiento=date(hoy.year - (7 + indice * 2), 9, 10),
                id_categoria=categoria.id_categoria, estado="Retirado" if indice == 3 else "Activo",
                beca=beca, tutor=tutor.nombre,
            )
            alumno.equipos = [equipo]; db.session.add(alumno); db.session.flush()
            db.session.add_all([
                AlumnoTutor(alumno=alumno, tutor=tutor, principal=True),
                InscripcionGestion(id_alumno=alumno.id_alumno, gestion=hoy.year, fecha_inscripcion=hoy-timedelta(days=120),
                                   estado="Retirada" if indice == 3 else "Activa", id_categoria=categoria.id_categoria,
                                   id_equipo_principal=equipo.id_equipo, monto_tarifa=Decimal("130"), porcentaje_beca=porcentaje,
                                   observacion="Caso de demostración"),
                HistorialCategoriaAlumno(id_alumno=alumno.id_alumno, id_categoria=categoria.id_categoria,
                                         fecha_inicio=hoy-timedelta(days=120), tipo_asignacion="Manual", motivo="Caso demo"),
                HistorialEquipoAlumno(id_alumno=alumno.id_alumno, id_equipo=equipo.id_equipo, gestion=hoy.year,
                                      fecha_inicio=hoy-timedelta(days=120), principal=True),
            ])
            if porcentaje:
                db.session.add(BecaHistorial(id_alumno=alumno.id_alumno, porcentaje=porcentaje,
                                             fecha_inicio=hoy-timedelta(days=120), estado="Activa", motivo="Beca demo"))
        alumnos.append(alumno)

    obtener(Tarifa, concepto="Mensualidad", fecha_inicio=date(hoy.year, 1, 1), id_categoria=categoria.id_categoria,
            defaults={"monto": Decimal("130"), "activo": True})
    periodos = [(hoy.replace(day=1) - timedelta(days=1)).strftime("%Y-%m"), hoy.strftime("%Y-%m")]
    obtener(Obligacion, id_alumno=alumnos[0].id_alumno, concepto="Mensualidad", periodo=periodos[0], defaults={
        "monto_original": Decimal("130"), "descuento": 0, "recargo": 0, "cubierto_beca": False, "fecha_vencimiento": hoy-timedelta(days=5)})
    obtener(Obligacion, id_alumno=alumnos[1].id_alumno, concepto="Mensualidad", periodo=periodos[1], defaults={
        "monto_original": Decimal("130"), "descuento": Decimal("130"), "recargo": 0, "cubierto_beca": True, "fecha_vencimiento": hoy+timedelta(days=20)})
    parcial = obtener(Obligacion, id_alumno=alumnos[2].id_alumno, concepto="Mensualidad", periodo=periodos[1], defaults={
        "monto_original": Decimal("130"), "descuento": 0, "recargo": 0, "cubierto_beca": False, "fecha_vencimiento": hoy+timedelta(days=20)})
    pago = Pago.query.filter_by(id_alumno=alumnos[2].id_alumno, mes_pagado=periodos[1], numero_operacion="DEMO-PARCIAL").first()
    if not pago:
        pago = Pago(id_alumno=alumnos[2].id_alumno, fecha_pago=hoy, fecha_vencimiento=hoy+timedelta(days=20),
                    mes_pagado=periodos[1], modo_pago="Efectivo", monto=Decimal("60"), numero_operacion="DEMO-PARCIAL")
        db.session.add(pago); db.session.flush(); db.session.add(AplicacionPago(obligacion=parcial, pago=pago, monto=Decimal("60")))

    entrenamiento = Entrenamiento.query.filter_by(id_entrenador=entrenador.id_personal).first()
    if not entrenamiento:
        entrenamiento = Entrenamiento(dia_semana=hoy.weekday(), hora_inicio=time(16, 0), hora_fin=time(17, 30),
                                      id_categoria=categoria.id_categoria, id_equipo=equipo.id_equipo,
                                      id_entrenador=entrenador.id_personal, lugar="[DEMO] Cancha de práctica", activo=True)
        db.session.add(entrenamiento); db.session.flush()
    for dias, estado_sesion in ((-7, "Realizada"), (0, "Realizada"), (7, "Programada")):
        fecha_sesion = hoy + timedelta(days=dias)
        sesion = obtener(SesionEntrenamiento, id_entrenamiento=entrenamiento.id_entrenamiento, fecha=fecha_sesion,
                         defaults={"estado": estado_sesion, "observacion": "Sesión demo"})
        if estado_sesion == "Realizada":
            for i, alumno in enumerate(alumnos[:3]):
                obtener(AsistenciaEntrenamiento, id_sesion_entrenamiento=sesion.id_sesion_entrenamiento,
                        id_alumno=alumno.id_alumno, defaults={"estado": ("Presente", "Justificado", "Tarde")[i],
                                                             "justificacion": "Caso demostrativo" if i else None})

    for concepto, categoria_nombre, monto, frecuencia, intervalo, dia, proveedor, activo in (
        ("[DEMO] Alquiler mensual", "Alquiler", 900, "Mensual", None, 30, proveedor_cancha, True),
        ("[DEMO] Pago quincenal entrenador", "Pago a profesores", 350, "Dias", 15, None, None, True),
        ("[DEMO] Servicio pausado", "Equipo deportivo", 180, "Mensual", None, 10, None, False),
    ):
        programado = obtener(PagoProgramado, concepto=concepto, defaults={
            "categoria": categoria_nombre, "id_categoria_contable": categorias[categoria_nombre].id_categoria_contable,
            "monto": Decimal(monto), "id_proveedor": proveedor.id_proveedor if proveedor else None,
            "modo_pago": "Efectivo", "frecuencia": frecuencia, "intervalo_dias": intervalo,
            "dia_mes": dia, "fecha_inicio": hoy-timedelta(days=45), "proxima_fecha": hoy+timedelta(days=15), "activo": activo,
        })
        for offset, estado in ((-30, "Pagado"), (-15, "Omitido"), (15, "Pendiente")):
            obtener(CuotaProgramada, id_programado=programado.id_programado, fecha_vencimiento=hoy+timedelta(days=offset),
                    defaults={"monto": programado.monto, "estado": estado,
                              "fecha_pago": hoy+timedelta(days=offset) if estado == "Pagado" else None,
                              "motivo_omision": "Caso omitido demo" if estado == "Omitido" else None})

    producto = obtener(Producto, codigo="DEMO-UNIFORME", defaults={"nombre": "[DEMO] Camiseta de entrenamiento", "categoria": "Uniformes", "activo": True})
    variante_m = obtener(ProductoVariante, id_producto=producto.id_producto, talla="M", color="Azul", defaults={"precio_compra": 50, "precio_venta": 90, "stock": 12, "stock_minimo": 3})
    variante_l = obtener(ProductoVariante, id_producto=producto.id_producto, talla="L", color="Blanco", defaults={"precio_compra": 50, "precio_venta": 90, "stock": 2, "stock_minimo": 3})
    compra = Compra.query.filter_by(numero_factura="DEMO-COMPRA-001").first()
    if not compra:
        compra = Compra(proveedor=proveedor_uniformes, fecha=hoy-timedelta(days=20), numero_factura="DEMO-COMPRA-001", modo_pago="Efectivo", total=Decimal("500"), observacion="Compra demo")
        db.session.add(compra); db.session.flush()
        db.session.add(DetalleCompra(compra=compra, variante=variante_m, cantidad=10, costo_unitario=50, subtotal=500))
    venta = Venta.query.filter_by(numero_operacion="DEMO-VENTA-001").first()
    if not venta:
        venta = Venta(alumno=alumnos[0], fecha=hoy-timedelta(days=3), modo_pago="Efectivo", numero_operacion="DEMO-VENTA-001", subtotal=180, descuento=10, total=170, observacion="Venta demo con descuento")
        db.session.add(venta); db.session.flush()
        detalle = DetalleVenta(venta=venta, variante=variante_m, cantidad=2, precio_unitario=90, subtotal=180)
        db.session.add(detalle); db.session.flush()
        anterior=variante_m.stock; variante_m.stock -= 2
        db.session.add(MovimientoInventario(variante=variante_m, tipo="Venta", cantidad=-2, stock_anterior=anterior, stock_nuevo=variante_m.stock, origen_tipo="Venta", origen_id=venta.id_venta))
        devolucion = DevolucionVenta(venta=venta, fecha=hoy-timedelta(days=1), total_credito=90, motivo="Cambio de talla demo")
        db.session.add(devolucion); db.session.flush(); db.session.add(DetalleDevolucionVenta(devolucion=devolucion, detalle_venta=detalle, cantidad=1, subtotal=90))
        anterior=variante_m.stock; variante_m.stock += 1
        db.session.add(MovimientoInventario(variante=variante_m, tipo="Devolución", cantidad=1, stock_anterior=anterior, stock_nuevo=variante_m.stock, origen_tipo="DevolucionVenta", origen_id=devolucion.id_devolucion))
    if not ConteoInventario.query.filter_by(observacion="[DEMO] Conteo pendiente").first():
        pendiente = ConteoInventario(fecha=hoy, estado="Pendiente", observacion="[DEMO] Conteo pendiente")
        aprobado = ConteoInventario(fecha=hoy-timedelta(days=2), estado="Aprobado", observacion="[DEMO] Conteo aprobado")
        db.session.add_all([pendiente, aprobado]); db.session.flush()
        db.session.add_all([
            DetalleConteoInventario(conteo=pendiente, variante=variante_m, stock_sistema=variante_m.stock, stock_contado=variante_m.stock-1),
            DetalleConteoInventario(conteo=pendiente, variante=variante_l, stock_sistema=variante_l.stock, stock_contado=variante_l.stock),
            DetalleConteoInventario(conteo=aprobado, variante=variante_m, stock_sistema=variante_m.stock, stock_contado=variante_m.stock),
        ])
    for tipo, categoria_nombre, concepto, monto, offset in (
        ("Ingreso", "Mensualidades", "[DEMO] Ingreso mensualidad", 130, -2),
        ("Ingreso", "Uniformes", "[DEMO] Venta uniforme", 170, -1),
        ("Egreso", "Alquiler", "[DEMO] Pago alquiler", 1200, -5),
        ("Egreso", "Pago a profesores", "[DEMO] Pago entrenador", 650, -3),
    ):
        if not MovimientoContable.query.filter_by(concepto=concepto).first():
            db.session.add(MovimientoContable(tipo=tipo, categoria=categoria_nombre,
                id_categoria_contable=categorias[categoria_nombre].id_categoria_contable,
                concepto=concepto, monto=Decimal(monto), fecha=hoy+timedelta(days=offset), modo_pago="Efectivo"))
    db.session.add(Auditoria(modulo="Sistema", accion=MARCA, detalle="Casos de prueba de módulos nuevos"))
    db.session.commit()
    print("Datos demo cargados correctamente.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        try:
            ejecutar()
        except Exception:
            db.session.rollback()
            raise
