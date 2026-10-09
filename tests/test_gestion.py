from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Alumno, Auditoria, Categoria, CategoriaContable, CierreCaja, Compra, Configuracion, CuotaProgramada, DevolucionVenta, MovimientoCaja, MovimientoContable, MovimientoInventario, Obligacion, Pago, PagoProgramado, Producto, ProductoVariante, Proveedor, SesionCaja, Usuario, Venta


def _variante(stock=5):
    producto = Producto(codigo="UNI-001", nombre="Camiseta", categoria="Uniformes")
    variante = ProductoVariante(
        producto=producto, talla="M", color="Azul", precio_compra=Decimal("40"),
        precio_venta=Decimal("70"), stock=stock, stock_minimo=1,
    )
    db.session.add(producto)
    db.session.commit()
    return variante


def test_alerta_stock_se_actualiza_al_crear_y_reponer_producto(client, app):
    respuesta = client.post("/gestion/inventario/producto", data={
        "codigo": "BAL-001", "nombre": "Balón", "categoria": "Equipo deportivo",
        "talla": "Única", "color": "Blanco", "precio_compra": "80",
        "precio_venta": "110", "stock_inicial": "0", "stock_minimo": "2",
    })
    assert respuesta.status_code == 302
    inventario = client.get("/gestion/inventario")
    assert b"Sin stock" in inventario.data
    assert b"1 stock bajo" in client.get("/informacion/").data

    with app.app_context():
        variante = ProductoVariante.query.one()
        id_variante = variante.id_variante
        assert Auditoria.query.filter_by(
            modulo="Inventario", accion="Crear producto"
        ).count() == 1

    respuesta = client.post(f"/gestion/inventario/{id_variante}/movimiento", data={
        "tipo": "Entrada", "cantidad": "3", "motivo": "Reposición",
    })
    assert respuesta.status_code == 302
    inventario = client.get("/gestion/inventario")
    assert b"Disponible" in inventario.data
    assert b"Sin stock" not in inventario.data
    assert b"0 stock bajo" in client.get("/informacion/").data


def test_editar_precios_de_variante_registra_auditoria(client, app):
    with app.app_context():
        variante = _variante(stock=4)
        id_variante = variante.id_variante

    respuesta = client.post(f"/gestion/inventario/{id_variante}/precios", data={
        "precio_compra": "45.50", "precio_venta": "79.90",
    })
    assert respuesta.status_code == 302
    with app.app_context():
        variante = db.session.get(ProductoVariante, id_variante)
        assert variante.precio_compra == Decimal("45.50")
        assert variante.precio_venta == Decimal("79.90")
        auditoria = Auditoria.query.filter_by(
            modulo="Inventario", accion="Editar precios",
            entidad="ProductoVariante", id_entidad=id_variante,
        ).one()
        assert "compra=40.00" in auditoria.valor_anterior
        assert "venta=79.90" in auditoria.valor_nuevo


def test_movimiento_manual_y_exportaciones(client, app):
    respuesta = client.post("/gestion/contabilidad/nuevo", data={
        "tipo": "Egreso", "categoria": "Servicios", "concepto": "Electricidad",
        "monto": "125.50", "fecha": "2026-08-14", "modo_pago": "QR",
        "comprobante": (BytesIO(b"%PDF-1.4 prueba"), "factura.pdf"),
    })
    assert respuesta.status_code == 302
    with app.app_context():
        movimiento = MovimientoContable.query.one()
        assert movimiento.tipo == "Egreso"
        assert movimiento.monto == Decimal("125.50")
        assert movimiento.comprobante.endswith(".pdf")
        id_movimiento = movimiento.id_movimiento
    assert client.get(f"/gestion/contabilidad/{id_movimiento}/comprobante").status_code == 200
    assert client.get("/gestion/contabilidad/exportar.pdf?columnas=fecha&columnas=monto").data.startswith(b"%PDF")
    assert client.get("/gestion/contabilidad/exportar.xlsx?columnas=fecha&columnas=monto").status_code == 200
    respuesta = client.get("/gestion/contabilidad?mes_resumen=2026-05")
    assert respuesta.status_code == 200
    assert b'Mes del resumen' in respuesta.data
    assert b'05/2026' in respuesta.data
    assert b'No hay movimientos en este mes' in respuesta.data
    assert b'<table' not in respuesta.data
    ampliada = client.get("/gestion/contabilidad?vista=movimientos&mes_resumen=2026-05")
    assert ampliada.status_code == 200
    assert b'<table' in ampliada.data
    assert b'Volver al resumen' in ampliada.data


def test_crear_categoria_contable_y_agrupar_movimientos(client):
    respuesta = client.post("/gestion/contabilidad/categorias", data={
        "nombre": "Compra de equipo deportivo", "tipo": "Egreso",
    })
    assert respuesta.status_code == 302
    client.post("/gestion/contabilidad/nuevo", data={
        "tipo": "Egreso", "categoria": "Compra de equipo deportivo",
        "concepto": "Compra de balones", "monto": "300",
        "fecha": "2026-08-15", "modo_pago": "Efectivo",
    })
    respuesta = client.get("/gestion/contabilidad?mes_resumen=2026-08")
    assert b'Compra de equipo deportivo' in respuesta.data
    assert b'Compra de balones' in respuesta.data
    assert b'Total 300.00' in respuesta.data
    with client.application.app_context():
        categoria = CategoriaContable.query.filter_by(nombre="Compra de equipo deportivo").one()
        id_categoria = categoria.id_categoria_contable
    respuesta = client.post(f"/gestion/contabilidad/categorias/{id_categoria}/tipo", data={
        "nombre": "Material deportivo", "tipo": "Ambos",
    })
    assert respuesta.status_code == 302
    with client.application.app_context():
        movimiento = MovimientoContable.query.one()
        assert movimiento.categoria == "Compra de equipo deportivo"
        assert movimiento.categoria_rel.nombre == "Material deportivo"
    assert client.get("/gestion/proveedores").status_code == 200
    assert client.get("/gestion/inventario").status_code == 200
    assert client.get("/gestion/ventas").status_code == 200


def test_mensualidad_crea_ingreso_y_anular_pago_lo_excluye(client, app):
    with app.app_context():
        config = Configuracion.obtener()
        config.monto_mensualidad = Decimal("200")
        categoria = Categoria.query.first()
        alumno = Alumno(nombre="Ana", apellido="Prueba", fecha_nacimiento=date(2014, 4, 5), id_categoria=categoria.id_categoria)
        db.session.add(alumno)
        db.session.commit()
        id_alumno = alumno.id_alumno
    respuesta = client.post(f"/pagos/alumno/{id_alumno}/nuevo", data={
        "mes_pagado": "2026-08", "modo_pago": "Efectivo", "fecha_pago": date.today().isoformat(),
    })
    assert respuesta.status_code == 302
    with app.app_context():
        pago = Pago.query.one()
        id_pago = pago.id_pago
        ingreso = MovimientoContable.query.filter_by(origen_tipo="Pago", origen_id=id_pago).one()
        assert ingreso.monto == Decimal("200.00")
        assert ingreso.activo
    client.post(f"/pagos/{id_pago}/eliminar", data={"motivo": "Registro equivocado"})
    with app.app_context():
        assert not MovimientoContable.query.filter_by(origen_tipo="Pago", origen_id=id_pago).one().activo


def test_mensualidad_admite_dos_abonos_y_solo_cubre_al_completar(client, app):
    with app.app_context():
        config = Configuracion.obtener()
        config.monto_mensualidad = Decimal("200")
        categoria = Categoria.query.first()
        alumno = Alumno(nombre="Abono", apellido="Parcial", fecha_nacimiento=date(2014, 4, 5), id_categoria=categoria.id_categoria)
        db.session.add(alumno)
        db.session.flush()
        id_alumno = alumno.id_alumno
        db.session.commit()
    primero = client.post(f"/pagos/alumno/{id_alumno}/nuevo", data={
        "mes_pagado": "2026-08", "modo_pago": "Efectivo",
        "fecha_pago": date.today().isoformat(), "monto_abono": "80",
    })
    assert primero.status_code == 302
    with app.app_context():
        obligacion = Obligacion.query.one()
        assert obligacion.estado == "Parcial"
        assert obligacion.saldo == Decimal("120.00")
        assert db.session.get(Alumno, id_alumno).estado_mensualidad == "Sin pagos"
    segundo = client.post(f"/pagos/alumno/{id_alumno}/nuevo", data={
        "mes_pagado": "2026-08", "modo_pago": "QR", "numero_operacion": "ABONO-2",
        "monto_abono": "120",
    })
    assert segundo.status_code == 302
    with app.app_context():
        obligacion = Obligacion.query.one()
        assert obligacion.estado == "Pagada"
        assert obligacion.saldo == 0
        assert Pago.query.count() == 2
        assert sum(m.monto for m in MovimientoContable.query.filter_by(origen_tipo="Pago").all()) == Decimal("200.00")


def test_caja_exige_apertura_vincula_movimiento_y_cierra_turno(client, app):
    app.config["AUTH_REQUIRED"] = True
    client.post("/acceso/", data={"nombre_usuario": "admin", "contrasena": "00000"})
    with app.app_context():
        Usuario.query.filter_by(nombre_usuario="admin").one().debe_cambiar_clave = False
        Configuracion.obtener().monto_mensualidad = Decimal("130")
        categoria = Categoria.query.first()
        alumno = Alumno(nombre="Caja", apellido="Turno", fecha_nacimiento=date(2014, 4, 5), id_categoria=categoria.id_categoria)
        db.session.add(alumno); db.session.commit(); id_alumno = alumno.id_alumno
    bloqueado = client.post(f"/pagos/alumno/{id_alumno}/nuevo", data={
        "mes_pagado": "2026-08", "modo_pago": "Efectivo", "fecha_pago": date.today().isoformat(),
    })
    assert bloqueado.location.endswith("/pagos/caja")
    with app.app_context():
        assert Pago.query.count() == 0
    client.post("/pagos/caja/abrir", data={"saldo_inicial": "300", "observacion": "Turno mañana"})
    client.post(f"/pagos/alumno/{id_alumno}/nuevo", data={
        "mes_pagado": "2026-08", "modo_pago": "Efectivo", "fecha_pago": date.today().isoformat(),
    })
    with app.app_context():
        sesion = SesionCaja.query.one()
        assert sesion.estado == "Abierta"
        assert sesion.esperado_actual == Decimal("430.00")
        assert MovimientoCaja.query.one().id_sesion == sesion.id_sesion
    client.post("/pagos/caja", data={
        "fecha": date.today().isoformat(), "efectivo_contado": "430",
        "qr_confirmado": "0", "observacion": "Sin diferencia",
    })
    with app.app_context():
        sesion = SesionCaja.query.one()
        assert sesion.estado == "Cerrada"
        assert sesion.diferencia == 0


def test_nueva_sesion_abierta_permite_pagar_aunque_exista_cierre_del_dia(client, app):
    app.config["AUTH_REQUIRED"] = True
    client.post("/acceso/", data={"nombre_usuario": "admin", "contrasena": "00000"})
    with app.app_context():
        Usuario.query.filter_by(nombre_usuario="admin").one().debe_cambiar_clave = False
        Configuracion.obtener().monto_mensualidad = Decimal("130")
        categoria = Categoria.query.first()
        alumno = Alumno(
            nombre="Caja", apellido="Nueva sesión", fecha_nacimiento=date(2014, 4, 5),
            id_categoria=categoria.id_categoria,
        )
        db.session.add(alumno)
        db.session.add(CierreCaja(
            fecha=date.today(), efectivo_sistema=0, qr_sistema=0,
            efectivo_contado=0, qr_confirmado=0, diferencia=0,
        ))
        db.session.commit()
        id_alumno = alumno.id_alumno

    client.post("/pagos/caja/abrir", data={"saldo_inicial": "0"})
    respuesta = client.post(f"/pagos/alumno/{id_alumno}/nuevo", data={
        "mes_pagado": date.today().strftime("%Y-%m"), "modo_pago": "Efectivo",
        "fecha_pago": date.today().isoformat(), "monto_abono": "100",
    })

    assert respuesta.status_code == 302
    assert "/pagos/caja" not in respuesta.location
    with app.app_context():
        assert Pago.query.filter_by(id_alumno=id_alumno).count() == 1


def test_venta_descuenta_stock_y_anulacion_lo_restituye(client, app):
    with app.app_context():
        variante = _variante()
        id_variante = variante.id_variante
    respuesta = client.post("/gestion/ventas/nueva", data={
        "fecha": date.today().isoformat(), "cliente_externo": "Cliente prueba",
        "modo_pago": "Efectivo", "descuento": "10", "id_variante": [str(id_variante)],
        "cantidad": ["2"],
    })
    assert respuesta.status_code == 302
    with app.app_context():
        venta = Venta.query.one()
        id_venta = venta.id_venta
        assert db.session.get(ProductoVariante, id_variante).stock == 3
        ingreso = MovimientoContable.query.filter_by(origen_tipo="Venta", origen_id=id_venta).one()
        assert ingreso.monto == Decimal("130.00")
        assert MovimientoInventario.query.filter_by(tipo="Venta").count() == 1
    assert client.get(f"/gestion/ventas/{id_venta}/recibo.pdf").data.startswith(b"%PDF")
    client.post(f"/gestion/ventas/{id_venta}/anular", data={"motivo": "Error de carga"})
    with app.app_context():
        assert db.session.get(ProductoVariante, id_variante).stock == 5
        assert not db.session.get(Venta, id_venta).activo
        assert not MovimientoContable.query.filter_by(origen_tipo="Venta", origen_id=id_venta).one().activo


def test_compra_formal_aumenta_stock_crea_egreso_y_se_puede_anular(client, app):
    with app.app_context():
        variante = _variante(stock=2)
        proveedor = Proveedor(nombre="Proveedor deportivo", activo=True)
        db.session.add(proveedor); db.session.commit()
        id_variante, id_proveedor = variante.id_variante, proveedor.id_proveedor
    respuesta = client.post("/gestion/compras/nueva", data={
        "id_proveedor": str(id_proveedor), "fecha": date.today().isoformat(),
        "numero_factura": "F-100", "modo_pago": "Efectivo",
        "id_variante": [str(id_variante)], "cantidad": ["5"], "costo_unitario": ["40"],
    })
    assert respuesta.status_code == 302
    with app.app_context():
        compra = Compra.query.one(); id_compra = compra.id_compra
        assert compra.total == Decimal("200.00")
        assert db.session.get(ProductoVariante, id_variante).stock == 7
        assert MovimientoContable.query.filter_by(origen_tipo="Compra", origen_id=id_compra).one().monto == Decimal("200.00")
    client.post(f"/gestion/compras/{id_compra}/anular", data={"motivo": "Factura incorrecta"})
    with app.app_context():
        assert not db.session.get(Compra, id_compra).activo
        assert db.session.get(ProductoVariante, id_variante).stock == 2
        assert not MovimientoContable.query.filter_by(origen_tipo="Compra", origen_id=id_compra).one().activo


def test_fallo_al_guardar_compra_revierte_stock_y_egreso(client, app, monkeypatch):
    with app.app_context():
        variante = _variante(stock=4)
        proveedor = Proveedor(nombre="Proveedor fallo", activo=True)
        db.session.add(proveedor); db.session.commit()
        id_variante, id_proveedor = variante.id_variante, proveedor.id_proveedor
        clase_sesion = type(db.session())
    def fallar_commit(self):
        raise SQLAlchemyError("fallo simulado")
    monkeypatch.setattr(clase_sesion, "commit", fallar_commit)
    respuesta = client.post("/gestion/compras/nueva", data={
        "id_proveedor": str(id_proveedor), "fecha": date.today().isoformat(),
        "modo_pago": "Efectivo", "id_variante": [str(id_variante)],
        "cantidad": ["3"], "costo_unitario": ["40"],
    }, follow_redirects=True)
    assert b"ning" in respuesta.data.lower()
    with app.app_context():
        assert db.session.get(ProductoVariante, id_variante).stock == 4
        assert Compra.query.count() == 0
        assert MovimientoContable.query.filter_by(origen_tipo="Compra").count() == 0


def test_venta_rechaza_stock_negativo_incluso_con_lineas_repetidas(client, app):
    with app.app_context():
        id_variante = _variante(stock=3).id_variante
    respuesta = client.post("/gestion/ventas/nueva", data={
        "fecha": date.today().isoformat(), "cliente_externo": "Cliente prueba",
        "modo_pago": "Efectivo", "descuento": "0",
        "id_variante": [str(id_variante), str(id_variante)], "cantidad": ["2", "2"],
    }, follow_redirects=True)
    assert b"stock suficiente" in respuesta.data
    with app.app_context():
        assert db.session.get(ProductoVariante, id_variante).stock == 3
        assert Venta.query.count() == 0


def test_pago_cada_quince_dias_genera_cuotas_y_pagar_crea_egreso(client, app):
    hoy = date.today()
    respuesta = client.post("/gestion/pagos-programados/nuevo", data={
        "concepto": "Pago profesor", "categoria": "Sueldos", "monto": "500",
        "modo_pago": "Transferencia", "frecuencia": "Dias", "intervalo_dias": "15",
        "fecha_inicio": hoy.isoformat(), "fecha_fin": "", "observacion": "Profesor A",
    })
    assert respuesta.status_code == 302
    with app.app_context():
        programado = PagoProgramado.query.one()
        cuotas = CuotaProgramada.query.order_by(CuotaProgramada.fecha_vencimiento).all()
        assert len(cuotas) == 25
        assert cuotas[1].fecha_vencimiento - cuotas[0].fecha_vencimiento == timedelta(days=15)
        id_cuota = cuotas[0].id_cuota
    respuesta = client.post(f"/gestion/pagos-programados/cuota/{id_cuota}/pagar", data={
        "fecha_pago": hoy.isoformat(), "modo_pago": "Transferencia", "numero_operacion": "TR-001",
    })
    assert respuesta.status_code == 302
    with app.app_context():
        cuota = db.session.get(CuotaProgramada, id_cuota)
        assert cuota.estado == "Pagado"
        movimiento = MovimientoContable.query.filter_by(origen_tipo="CuotaProgramada", origen_id=id_cuota).one()
        assert movimiento.tipo == "Egreso"
        assert movimiento.monto == Decimal("500.00")
    client.post(f"/gestion/pagos-programados/cuota/{id_cuota}/pagar", data={
        "fecha_pago": hoy.isoformat(), "modo_pago": "Efectivo",
    })
    with app.app_context():
        assert MovimientoContable.query.filter_by(origen_tipo="CuotaProgramada", origen_id=id_cuota).count() == 1


def test_pago_mensual_dia_31_ajusta_meses_cortos(client, app):
    client.post("/gestion/pagos-programados/nuevo", data={
        "concepto": "Alquiler", "categoria": "Alquileres", "monto": "1000",
        "modo_pago": "Efectivo", "frecuencia": "Mensual", "dia_mes": "31",
        "fecha_inicio": "2026-01-30", "fecha_fin": "2026-04-30",
    })
    with app.app_context():
        fechas = [c.fecha_vencimiento.isoformat() for c in CuotaProgramada.query.order_by(CuotaProgramada.fecha_vencimiento)]
        assert fechas == ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"]


def test_pendientes_oculta_cuotas_de_meses_futuros(client):
    hoy = date.today()
    siguiente_mes = date(hoy.year + (hoy.month == 12), 1 if hoy.month == 12 else hoy.month + 1, 1)
    programado = PagoProgramado(
        concepto="Servicio recurrente", categoria="Servicios", monto=Decimal("100"),
        modo_pago="Efectivo", frecuencia="Mensual", dia_mes=hoy.day,
        fecha_inicio=hoy,
    )
    db.session.add(programado)
    db.session.flush()
    db.session.add_all([
        CuotaProgramada(programado=programado, fecha_vencimiento=hoy, monto=Decimal("100")),
        CuotaProgramada(programado=programado, fecha_vencimiento=siguiente_mes, monto=Decimal("250")),
    ])
    db.session.commit()

    pendientes = client.get("/gestion/pagos-programados?estado=Pendiente")
    pendientes_siguiente_mes = client.get(
        "/gestion/pagos-programados",
        query_string={"estado": "Pendiente", "periodo": siguiente_mes.strftime("%Y-%m")},
    )
    todas = client.get("/gestion/pagos-programados?estado=Todos")

    assert hoy.strftime("%d/%m/%Y").encode() in pendientes.data
    assert siguiente_mes.strftime("%d/%m/%Y").encode() not in pendientes.data
    assert b"Total pendiente del per" in pendientes.data
    assert b"<h3>100.00</h3>" in pendientes.data
    assert siguiente_mes.strftime("%d/%m/%Y").encode() in pendientes_siguiente_mes.data
    assert b"<h3>250.00</h3>" in pendientes_siguiente_mes.data
    assert siguiente_mes.strftime("%d/%m/%Y").encode() in todas.data
    assert b"nicamente las cuotas del per" in pendientes.data


def test_venta_con_devolucion_parcial_no_puede_anularse(client, app):
    with app.app_context():
        variante = _variante(stock=5)
        id_variante = variante.id_variante
    respuesta = client.post("/gestion/ventas/nueva", data={
        "id_variante": [str(id_variante)], "cantidad": ["3"], "descuento": "0",
        "cliente_externo": "Cliente", "fecha": date.today().isoformat(), "modo_pago": "Efectivo",
    })
    assert respuesta.status_code == 302
    with app.app_context():
        venta = Venta.query.one()
        id_venta = venta.id_venta
        id_detalle = venta.detalles[0].id_detalle
    client.post(f"/gestion/ventas/{id_venta}/devolver", data={"id_detalle": id_detalle, "cantidad": 1, "motivo": "Cambio"})
    client.post(f"/gestion/ventas/{id_venta}/anular", data={"motivo": "Error"})
    with app.app_context():
        venta = db.session.get(Venta, id_venta)
        assert venta.activo
        assert db.session.get(ProductoVariante, id_variante).stock == 3
        assert MovimientoContable.query.filter_by(origen_tipo="Venta", origen_id=id_venta).one().activo


def test_venta_anulada_rechaza_devoluciones(client, app):
    with app.app_context():
        variante = _variante(stock=3)
        id_variante = variante.id_variante
    client.post("/gestion/ventas/nueva", data={
        "id_variante": [str(id_variante)], "cantidad": ["1"], "descuento": "0",
        "cliente_externo": "Cliente", "fecha": date.today().isoformat(), "modo_pago": "Efectivo",
    })
    with app.app_context():
        venta = Venta.query.one(); id_venta = venta.id_venta; id_detalle = venta.detalles[0].id_detalle
    client.post(f"/gestion/ventas/{id_venta}/anular", data={"motivo": "Error"})
    client.post(f"/gestion/ventas/{id_venta}/devolver", data={"id_detalle": id_detalle, "cantidad": 1, "motivo": "No válida"})
    with app.app_context():
        assert db.session.get(ProductoVariante, id_variante).stock == 3
        assert DevolucionVenta.query.count() == 0
