from datetime import date
from decimal import Decimal
from app.extensions import db
from app.models import CierreCaja, Pago, MovimientoContable, Auditoria


class RealizarCierreCajaUseCase:
    """Caso de uso: Cierre y arqueo diario de caja."""

    def ejecutar(self, fecha, efectivo_contado, qr_confirmado, observacion=None, id_usuario=None):
        if isinstance(fecha, str):
            fecha = date.fromisoformat(fecha)

        efectivo_contado = Decimal(str(efectivo_contado or 0))
        qr_confirmado = Decimal(str(qr_confirmado or 0))

        # Calcular totales según pagos activos del día
        pagos_dia = Pago.query.filter(
            Pago.fecha_pago == fecha, Pago.eliminado_en == None
        ).all()

        efectivo_sistema = sum(
            (p.monto for p in pagos_dia if p.modo_pago == "Efectivo"), Decimal("0.00")
        )
        qr_sistema = sum(
            (p.monto for p in pagos_dia if p.modo_pago == "QR"), Decimal("0.00")
        )

        diferencia = (efectivo_contado + qr_confirmado) - (efectivo_sistema + qr_sistema)

        cierre = CierreCaja.query.filter_by(fecha=fecha).first()
        if not cierre:
            cierre = CierreCaja(fecha=fecha)
            db.session.add(cierre)

        cierre.efectivo_sistema = efectivo_sistema
        cierre.qr_sistema = qr_sistema
        cierre.efectivo_contado = efectivo_contado
        cierre.qr_confirmado = qr_confirmado
        cierre.diferencia = diferencia
        cierre.observacion = observacion

        auditoria = Auditoria(
            modulo="Pagos",
            accion="Cierre de caja",
            entidad="CierreCaja",
            id_entidad=cierre.id_cierre,
            detalle=f"Cierre de caja {fecha}: Sistema Bs. {efectivo_sistema + qr_sistema}, Contado Bs. {efectivo_contado + qr_confirmado}, Dif. Bs. {diferencia}",
            id_usuario=id_usuario,
            valor_nuevo=f"Diferencia: Bs. {diferencia}",
        )
        db.session.add(auditoria)
        db.session.commit()

        return cierre
