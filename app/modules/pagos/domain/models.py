from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import validates
from app.extensions import db
from sqlalchemy import event, text
from app.utils.validacion import solo_numeros_opcional


def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


MODOS_PAGO = ["Efectivo", "QR"]
ESTADOS_PAGO = ["Vigente", "Próximo a vencer", "Pagado"]
ESTADOS_MENSUALIDAD = ["Vigente", "Próximo a vencer", "Vencido", "Retirado"]
MODOS_MOVIMIENTO = ["Efectivo", "QR", "Transferencia", "Otro"]


class Pago(db.Model):
    __tablename__ = "pago"
    __table_args__ = (
        db.Index("ix_pago_alumno_mes", "id_alumno", "mes_pagado"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR')", name="ck_pago_modo"),
        db.CheckConstraint("monto >= 0", name="ck_pago_monto"),
    )
    id_pago = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno"), nullable=False)
    es_beca = db.Column(db.Boolean, default=False)
    fecha_pago = db.Column(db.Date, nullable=False)
    hora_registro = db.Column(db.Time, default=lambda: datetime.now().time())
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    mes_pagado = db.Column(db.String(7), nullable=False)
    modo_pago = db.Column(db.String(10), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    creado_en = db.Column(db.DateTime, default=ahora_utc)
    eliminado_en = db.Column(db.DateTime, nullable=True)
    numero_operacion = db.Column(db.String(80), nullable=True)

    @property
    def activo(self):
        return self.eliminado_en is None

    @property
    def estado(self):
        if not self.activo:
            return "Anulado"
        if date.today() > self.fecha_vencimiento:
            return "Pagado"
        return self.estado_cobertura

    @property
    def estado_cobertura(self):
        hoy = date.today()
        if hoy > self.fecha_vencimiento:
            return "Vencido"
        from app.models import Configuracion
        config = Configuracion.obtener()
        dias_aviso = config.dias_proximo_vencimiento if config else 5
        if (self.fecha_vencimiento - hoy).days <= dias_aviso:
            return "Próximo a vencer"
        return "Vigente"

    def __repr__(self):
        return f"<Pago {self.id_pago} alumno={self.id_alumno} mes={self.mes_pagado}>"


class Obligacion(db.Model):
    """Deuda o concepto cobrable independiente de los abonos que la cancelan."""
    __tablename__ = "obligacion"
    __table_args__ = (
        db.UniqueConstraint("id_alumno", "concepto", "periodo", name="uq_obligacion_alumno_concepto_periodo"),
        db.CheckConstraint("monto_original >= 0 AND descuento >= 0 AND recargo >= 0", name="ck_obligacion_importes"),
    )
    id_obligacion = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="RESTRICT"), nullable=False)
    concepto = db.Column(db.String(40), nullable=False, default="Mensualidad")
    periodo = db.Column(db.String(7), nullable=False)
    monto_original = db.Column(db.Numeric(10, 2), nullable=False)
    descuento = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    recargo = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    cubierto_beca = db.Column(db.Boolean, nullable=False, default=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    alumno = db.relationship("Alumno", backref=db.backref("obligaciones", lazy=True))
    aplicaciones = db.relationship("AplicacionPago", back_populates="obligacion", cascade="all, delete-orphan")

    @property
    def total(self):
        return max(Decimal("0.00"), Decimal(self.monto_original or 0) - Decimal(self.descuento or 0) + Decimal(self.recargo or 0))

    @property
    def pagado(self):
        return sum((Decimal(a.monto or 0) for a in self.aplicaciones if a.pago and a.pago.activo), Decimal("0.00"))

    @property
    def saldo(self):
        return max(Decimal("0.00"), self.total - self.pagado)

    @property
    def estado(self):
        if self.cubierto_beca:
            return "Cubierto por beca"
        if self.saldo <= 0:
            return "Pagada"
        if self.pagado > 0:
            return "Parcial"
        return "Pendiente"


class AplicacionPago(db.Model):
    __tablename__ = "aplicacion_pago"
    id_aplicacion = db.Column(db.Integer, primary_key=True)
    id_obligacion = db.Column(db.Integer, db.ForeignKey("obligacion.id_obligacion", ondelete="RESTRICT"), nullable=False)
    id_pago = db.Column(db.Integer, db.ForeignKey("pago.id_pago", ondelete="RESTRICT"), nullable=False, unique=True)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    obligacion = db.relationship("Obligacion", back_populates="aplicaciones")
    pago = db.relationship("Pago", backref=db.backref("aplicacion", uselist=False))


class Tarifa(db.Model):
    __tablename__ = "tarifa"
    id_tarifa = db.Column(db.Integer, primary_key=True)
    concepto = db.Column(db.String(40), nullable=False, default="Mensualidad")
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)


class AnulacionPago(db.Model):
    """Reversión formal e inmutable de un pago."""
    __tablename__ = "anulacion_pago"
    id_anulacion = db.Column(db.Integer, primary_key=True)
    id_pago = db.Column(
        db.Integer, db.ForeignKey("pago.id_pago", ondelete="RESTRICT"),
        nullable=False, unique=True,
    )
    motivo = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    id_pago_reemplazo = db.Column(
        db.Integer, db.ForeignKey("pago.id_pago", ondelete="SET NULL"), nullable=True
    )
    pago = db.relationship("Pago", foreign_keys=[id_pago], backref=db.backref("anulacion", uselist=False))
    pago_reemplazo = db.relationship("Pago", foreign_keys=[id_pago_reemplazo])


class CierreCaja(db.Model):
    __tablename__ = "cierre_caja"
    __table_args__ = (
        db.CheckConstraint("efectivo_sistema >= 0 AND qr_sistema >= 0", name="ck_cierre_sistema"),
        db.CheckConstraint("efectivo_contado >= 0 AND qr_confirmado >= 0", name="ck_cierre_contado"),
    )
    id_cierre = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, unique=True)
    efectivo_sistema = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    qr_sistema = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    efectivo_contado = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    qr_confirmado = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    diferencia = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    observacion = db.Column(db.String(255), nullable=True)
    cerrado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    reabierto_en = db.Column(db.DateTime, nullable=True)
    motivo_reapertura = db.Column(db.String(255), nullable=True)


class SesionCaja(db.Model):
    __tablename__ = "sesion_caja"
    __table_args__ = (
        db.CheckConstraint("estado IN ('Abierta','Cerrada','Reabierta')", name="ck_sesion_caja_estado"),
        db.CheckConstraint("saldo_inicial >= 0", name="ck_sesion_caja_saldo_inicial"),
    )
    id_sesion = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"), nullable=False)
    abierta_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    saldo_inicial = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    cerrada_en = db.Column(db.DateTime, nullable=True)
    efectivo_esperado = db.Column(db.Numeric(12, 2), nullable=True)
    efectivo_contado = db.Column(db.Numeric(12, 2), nullable=True)
    diferencia = db.Column(db.Numeric(12, 2), nullable=True)
    estado = db.Column(db.String(12), nullable=False, default="Abierta")
    observacion = db.Column(db.String(255), nullable=True)
    motivo_reapertura = db.Column(db.String(255), nullable=True)
    id_cierre_legacy = db.Column(db.Integer, db.ForeignKey("cierre_caja.id_cierre", ondelete="SET NULL"), nullable=True, unique=True)
    usuario = db.relationship("Usuario")
    movimientos_caja = db.relationship("MovimientoCaja", back_populates="sesion")

    @property
    def ingresos_efectivo(self):
        return sum((Decimal(m.monto) for m in self.movimientos_caja if m.activo and m.tipo == "Ingreso" and m.modo_pago == "Efectivo"), Decimal("0"))

    @property
    def egresos_efectivo(self):
        return sum((Decimal(m.monto) for m in self.movimientos_caja if m.activo and m.tipo == "Egreso" and m.modo_pago == "Efectivo"), Decimal("0"))

    @property
    def esperado_actual(self):
        return Decimal(self.saldo_inicial or 0) + self.ingresos_efectivo - self.egresos_efectivo


class MovimientoCaja(db.Model):
    __tablename__ = "movimiento_caja"
    id_movimiento_caja = db.Column(db.Integer, primary_key=True)
    id_sesion = db.Column(db.Integer, db.ForeignKey("sesion_caja.id_sesion", ondelete="RESTRICT"), nullable=False)
    id_movimiento_contable = db.Column(db.Integer, db.ForeignKey("movimiento_contable.id_movimiento", ondelete="RESTRICT"), nullable=False, unique=True)
    tipo = db.Column(db.String(10), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    modo_pago = db.Column(db.String(20), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    sesion = db.relationship("SesionCaja", back_populates="movimientos_caja")
    movimiento_contable = db.relationship("MovimientoContable")

    @property
    def activo(self):
        return bool(self.movimiento_contable and self.movimiento_contable.activo)


class Proveedor(db.Model):
    __tablename__ = "proveedor"
    __table_args__ = (db.CheckConstraint("length(trim(nombre)) > 0", name="ck_proveedor_nombre"),)
    id_proveedor = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)
    tipo_persona = db.Column(db.String(10), nullable=False, default="Persona")
    documento = db.Column(db.String(40), nullable=True)
    correo = db.Column(db.String(120), nullable=True)
    contacto = db.Column(db.String(120), nullable=True)
    telefono = db.Column(db.String(50), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    observacion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    @validates("documento")
    def _validar_documento(self, key, valor):
        return solo_numeros_opcional(valor, "Documento", 40)

    @validates("telefono")
    def _validar_telefono(self, key, valor):
        return solo_numeros_opcional(valor, "Teléfono", 50)



class CategoriaContable(db.Model):
    __tablename__ = "categoria_contable"
    __table_args__ = (db.CheckConstraint("tipo IN ('Ingreso','Egreso','Ambos')", name="ck_categoria_contable_tipo"),)
    id_categoria_contable = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False, unique=True)
    tipo = db.Column(db.String(10), nullable=False, default="Ambos")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)


class MovimientoContable(db.Model):
    __tablename__ = "movimiento_contable"
    __table_args__ = (
        db.CheckConstraint("tipo IN ('Ingreso','Egreso')", name="ck_movimiento_tipo"),
        db.CheckConstraint("monto >= 0", name="ck_movimiento_monto"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR','Transferencia','Otro')", name="ck_movimiento_modo"),
        db.CheckConstraint("(origen_tipo IS NULL) = (origen_id IS NULL)", name="ck_movimiento_origen_completo"),
        db.UniqueConstraint("origen_tipo", "origen_id", name="uq_movimiento_origen"),
    )
    id_movimiento = db.Column(db.Integer, primary_key=True)
    id_sesion_caja = db.Column(db.Integer, db.ForeignKey("sesion_caja.id_sesion", ondelete="SET NULL"), nullable=True)
    tipo = db.Column(db.String(10), nullable=False)
    categoria = db.Column(db.String(80), nullable=False)
    id_categoria_contable = db.Column(db.Integer, db.ForeignKey("categoria_contable.id_categoria_contable", ondelete="RESTRICT"), nullable=True)
    concepto = db.Column(db.String(180), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    modo_pago = db.Column(db.String(20), nullable=False, default="Efectivo")
    numero_operacion = db.Column(db.String(100), nullable=True)
    id_proveedor = db.Column(db.Integer, db.ForeignKey("proveedor.id_proveedor"), nullable=True)
    comprobante = db.Column(db.String(255), nullable=True)
    observacion = db.Column(db.String(255), nullable=True)
    origen_tipo = db.Column(db.String(30), nullable=True)
    origen_id = db.Column(db.Integer, nullable=True)
    anulado_en = db.Column(db.DateTime, nullable=True)
    motivo_anulacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    proveedor = db.relationship("Proveedor")
    sesion_caja = db.relationship("SesionCaja")
    categoria_rel = db.relationship("CategoriaContable")

    @property
    def activo(self):
        return self.anulado_en is None


@event.listens_for(MovimientoContable, "before_insert")
def _vincular_sesion_caja(mapper, connection, objetivo):
    if objetivo.id_sesion_caja is not None:
        return
    try:
        from flask import has_request_context, session
        id_usuario = session.get("id_usuario") if has_request_context() else None
    except RuntimeError:
        id_usuario = None
    if id_usuario:
        objetivo.id_sesion_caja = connection.execute(text(
            "SELECT id_sesion FROM sesion_caja WHERE id_usuario=:u AND estado IN ('Abierta','Reabierta') ORDER BY abierta_en DESC LIMIT 1"
        ), {"u": id_usuario}).scalar()


@event.listens_for(MovimientoContable, "after_insert")
def _crear_movimiento_caja(mapper, connection, objetivo):
    if objetivo.id_sesion_caja:
        connection.execute(text("""INSERT INTO movimiento_caja
            (id_sesion,id_movimiento_contable,tipo,monto,modo_pago,creado_en)
            VALUES (:s,:m,:t,:n,:p,:c)"""), {
            "s": objetivo.id_sesion_caja, "m": objetivo.id_movimiento,
            "t": objetivo.tipo, "n": float(objetivo.monto), "p": objetivo.modo_pago,
            "c": objetivo.creado_en or ahora_utc(),
        })


class Producto(db.Model):
    __tablename__ = "producto"
    __table_args__ = (
        db.CheckConstraint("length(trim(codigo)) > 0", name="ck_producto_codigo"),
        db.CheckConstraint("length(trim(nombre)) > 0", name="ck_producto_nombre"),
    )
    id_producto = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(40), nullable=False, unique=True)
    nombre = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(80), nullable=False, default="Uniformes")
    descripcion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)


class ProductoVariante(db.Model):
    __tablename__ = "producto_variante"
    __table_args__ = (
        db.UniqueConstraint("id_producto", "talla", "color", name="uq_producto_variante"),
        db.CheckConstraint("stock >= 0", name="ck_variante_stock"),
        db.CheckConstraint("precio_compra >= 0 AND precio_venta >= 0", name="ck_variante_precios"),
        db.CheckConstraint("stock_minimo >= 0", name="ck_variante_stock_minimo"),
    )
    id_variante = db.Column(db.Integer, primary_key=True)
    id_producto = db.Column(db.Integer, db.ForeignKey("producto.id_producto", ondelete="CASCADE"), nullable=False)
    talla = db.Column(db.String(30), nullable=False, default="Única")
    color = db.Column(db.String(50), nullable=False, default="Estándar")
    precio_compra = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    precio_venta = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo = db.Column(db.Integer, nullable=False, default=0)
    producto = db.relationship("Producto", backref=db.backref("variantes", cascade="all, delete-orphan"))

    @property
    def nombre_completo(self):
        return f"{self.producto.nombre} - {self.talla} - {self.color}"


class MovimientoInventario(db.Model):
    __tablename__ = "movimiento_inventario"
    __table_args__ = (
        db.CheckConstraint("cantidad <> 0", name="ck_inventario_cantidad"),
        db.CheckConstraint("stock_anterior >= 0 AND stock_nuevo >= 0", name="ck_inventario_stock"),
        db.CheckConstraint("stock_nuevo = stock_anterior + cantidad", name="ck_inventario_balance"),
    )
    id_movimiento = db.Column(db.Integer, primary_key=True)
    id_variante = db.Column(db.Integer, db.ForeignKey("producto_variante.id_variante"), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    stock_anterior = db.Column(db.Integer, nullable=False)
    stock_nuevo = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(255), nullable=True)
    origen_tipo = db.Column(db.String(30), nullable=True)
    origen_id = db.Column(db.Integer, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    variante = db.relationship("ProductoVariante")


class ConteoInventario(db.Model):
    __tablename__ = "conteo_inventario"
    id_conteo = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    estado = db.Column(db.String(12), nullable=False, default="Pendiente")
    observacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)


class DetalleConteoInventario(db.Model):
    __tablename__ = "detalle_conteo_inventario"
    __table_args__ = (db.UniqueConstraint("id_conteo", "id_variante", name="uq_conteo_variante"),)
    id_detalle_conteo = db.Column(db.Integer, primary_key=True)
    id_conteo = db.Column(db.Integer, db.ForeignKey("conteo_inventario.id_conteo", ondelete="CASCADE"), nullable=False)
    id_variante = db.Column(db.Integer, db.ForeignKey("producto_variante.id_variante", ondelete="RESTRICT"), nullable=False)
    stock_sistema = db.Column(db.Integer, nullable=False)
    stock_contado = db.Column(db.Integer, nullable=False)
    conteo = db.relationship("ConteoInventario", backref=db.backref("detalles", cascade="all, delete-orphan"))
    variante = db.relationship("ProductoVariante")


class Compra(db.Model):
    __tablename__ = "compra"
    __table_args__ = (
        db.CheckConstraint("total >= 0", name="ck_compra_total"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR','Transferencia','Otro')", name="ck_compra_modo"),
    )
    id_compra = db.Column(db.Integer, primary_key=True)
    id_proveedor = db.Column(db.Integer, db.ForeignKey("proveedor.id_proveedor", ondelete="RESTRICT"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    numero_factura = db.Column(db.String(80), nullable=True)
    modo_pago = db.Column(db.String(20), nullable=False, default="Efectivo")
    total = db.Column(db.Numeric(12, 2), nullable=False)
    observacion = db.Column(db.String(255), nullable=True)
    anulado_en = db.Column(db.DateTime, nullable=True)
    motivo_anulacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    proveedor = db.relationship("Proveedor", backref=db.backref("compras", lazy=True))

    @property
    def activo(self):
        return self.anulado_en is None


class DetalleCompra(db.Model):
    __tablename__ = "detalle_compra"
    __table_args__ = (
        db.CheckConstraint("cantidad > 0", name="ck_detalle_compra_cantidad"),
        db.CheckConstraint("costo_unitario >= 0 AND subtotal >= 0", name="ck_detalle_compra_montos"),
        db.CheckConstraint("abs(subtotal-(costo_unitario*cantidad)) < 0.01", name="ck_detalle_compra_subtotal"),
    )
    id_detalle_compra = db.Column(db.Integer, primary_key=True)
    id_compra = db.Column(db.Integer, db.ForeignKey("compra.id_compra", ondelete="RESTRICT"), nullable=False)
    id_variante = db.Column(db.Integer, db.ForeignKey("producto_variante.id_variante", ondelete="RESTRICT"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    costo_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    compra = db.relationship("Compra", backref=db.backref("detalles", cascade="all, delete-orphan"))
    variante = db.relationship("ProductoVariante")


class Venta(db.Model):
    __tablename__ = "venta"
    __table_args__ = (
        db.CheckConstraint("subtotal >= 0 AND descuento >= 0 AND total >= 0", name="ck_venta_montos"),
        db.CheckConstraint("descuento <= subtotal", name="ck_venta_descuento"),
        db.CheckConstraint("abs(total - (subtotal - descuento)) < 0.01", name="ck_venta_total"),
        db.CheckConstraint("id_alumno IS NOT NULL OR length(trim(COALESCE(cliente_externo,''))) > 0", name="ck_venta_cliente"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR','Transferencia','Otro')", name="ck_venta_modo"),
    )
    id_venta = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno"), nullable=True)
    cliente_externo = db.Column(db.String(150), nullable=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    modo_pago = db.Column(db.String(20), nullable=False, default="Efectivo")
    numero_operacion = db.Column(db.String(100), nullable=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    descuento = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    observacion = db.Column(db.String(255), nullable=True)
    anulado_en = db.Column(db.DateTime, nullable=True)
    motivo_anulacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    alumno = db.relationship("Alumno", backref=db.backref("ventas", order_by="desc(Venta.fecha)"))

    @property
    def activo(self):
        return self.anulado_en is None


class DetalleVenta(db.Model):
    __tablename__ = "detalle_venta"
    __table_args__ = (
        db.CheckConstraint("cantidad > 0", name="ck_detalle_cantidad"),
        db.CheckConstraint("precio_unitario >= 0 AND subtotal >= 0", name="ck_detalle_montos"),
        db.CheckConstraint("abs(subtotal - (precio_unitario * cantidad)) < 0.01", name="ck_detalle_subtotal"),
    )
    id_detalle = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey("venta.id_venta", ondelete="CASCADE"), nullable=False)
    id_variante = db.Column(db.Integer, db.ForeignKey("producto_variante.id_variante"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    venta = db.relationship("Venta", backref=db.backref("detalles", cascade="all, delete-orphan"))
    variante = db.relationship("ProductoVariante")


class DevolucionVenta(db.Model):
    __tablename__ = "devolucion_venta"
    id_devolucion = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey("venta.id_venta", ondelete="RESTRICT"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    tipo = db.Column(db.String(12), nullable=False, default="Devolución")
    total_credito = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    motivo = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    venta = db.relationship("Venta", backref="devoluciones")


class DetalleDevolucionVenta(db.Model):
    __tablename__ = "detalle_devolucion_venta"
    id_detalle_devolucion = db.Column(db.Integer, primary_key=True)
    id_devolucion = db.Column(db.Integer, db.ForeignKey("devolucion_venta.id_devolucion", ondelete="CASCADE"), nullable=False)
    id_detalle_venta = db.Column(db.Integer, db.ForeignKey("detalle_venta.id_detalle", ondelete="RESTRICT"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    devolucion = db.relationship("DevolucionVenta", backref=db.backref("detalles", cascade="all, delete-orphan"))
    detalle_venta = db.relationship("DetalleVenta")


class PagoProgramado(db.Model):
    """Obligación recurrente que genera cuotas, no egresos anticipados."""
    __tablename__ = "pago_programado"
    __table_args__ = (
        db.CheckConstraint("monto > 0", name="ck_programado_monto"),
        db.CheckConstraint("frecuencia IN ('Dias','Mensual')", name="ck_programado_frecuencia"),
        db.CheckConstraint("intervalo_dias IS NULL OR intervalo_dias > 0", name="ck_programado_intervalo"),
        db.CheckConstraint("dia_mes IS NULL OR dia_mes BETWEEN 1 AND 31", name="ck_programado_dia_mes"),
        db.CheckConstraint("fecha_fin IS NULL OR fecha_fin >= fecha_inicio", name="ck_programado_fechas"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR','Transferencia','Otro')", name="ck_programado_modo"),
    )
    id_programado = db.Column(db.Integer, primary_key=True)
    concepto = db.Column(db.String(180), nullable=False)
    categoria = db.Column(db.String(80), nullable=False)
    id_categoria_contable = db.Column(db.Integer, db.ForeignKey("categoria_contable.id_categoria_contable", ondelete="RESTRICT"), nullable=True)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    id_proveedor = db.Column(db.Integer, db.ForeignKey("proveedor.id_proveedor"), nullable=True)
    modo_pago = db.Column(db.String(20), nullable=False, default="Efectivo")
    frecuencia = db.Column(db.String(10), nullable=False)
    intervalo_dias = db.Column(db.Integer, nullable=True)
    dia_mes = db.Column(db.Integer, nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    proxima_fecha = db.Column(db.Date, nullable=True)
    observacion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    proveedor = db.relationship("Proveedor")
    categoria_rel = db.relationship("CategoriaContable")


class CuotaProgramada(db.Model):
    __tablename__ = "cuota_programada"
    __table_args__ = (
        db.UniqueConstraint("id_programado", "fecha_vencimiento", name="uq_cuota_programada_fecha"),
        db.CheckConstraint("monto > 0", name="ck_cuota_programada_monto"),
        db.CheckConstraint("estado IN ('Pendiente','Pagado','Omitido')", name="ck_cuota_programada_estado"),
    )
    id_cuota = db.Column(db.Integer, primary_key=True)
    id_programado = db.Column(db.Integer, db.ForeignKey("pago_programado.id_programado", ondelete="CASCADE"), nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    estado = db.Column(db.String(12), nullable=False, default="Pendiente")
    fecha_pago = db.Column(db.Date, nullable=True)
    id_movimiento = db.Column(db.Integer, db.ForeignKey("movimiento_contable.id_movimiento", ondelete="SET NULL"), nullable=True, unique=True)
    motivo_omision = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    programado = db.relationship("PagoProgramado", backref=db.backref("cuotas", order_by="CuotaProgramada.fecha_vencimiento.desc()", cascade="all, delete-orphan"))
    movimiento = db.relationship("MovimientoContable")
