from datetime import datetime, timezone
from app.extensions import db
from app.models import Pago, AnulacionPago, MovimientoContable, Auditoria


def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AnularPagoUseCase:
    """Caso de uso: Anulación formal de un pago de mensualidad."""

    def ejecutar(self, id_pago, motivo, id_usuario=None):
        pago = Pago.query.get_or_404(id_pago)
        if not pago.activo:
            raise ValueError("El pago ya se encuentra anulado.")

        pago.eliminado_en = ahora_utc()

        anulacion = AnulacionPago(
            id_pago=pago.id_pago,
            motivo=motivo.strip(),
        )
        db.session.add(anulacion)

        # Anular movimiento contable originado por este pago
        mov = MovimientoContable.query.filter_by(
            origen_tipo="Pago", origen_id=pago.id_pago, anulado_en=None
        ).first()
        if mov:
            mov.anulado_en = ahora_utc()
            mov.motivo_anulacion = f"Pago #{pago.id_pago} anulado: {motivo}"

        auditoria = Auditoria(
            modulo="Pagos",
            accion="Anular pago",
            entidad="Pago",
            id_entidad=pago.id_pago,
            detalle=f"Se anuló el pago #{pago.id_pago} de {pago.alumno.nombre_completo}. Motivo: {motivo}",
            id_usuario=id_usuario,
            valor_anterior=f"Bs. {pago.monto}",
            valor_nuevo="Anulado",
        )
        db.session.add(auditoria)
        db.session.commit()

        return pago
