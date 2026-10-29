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

        # Anular movimiento contable originado por este pago si existe
        mov = MovimientoContable.query.filter_by(
            origen_tipo="Pago", origen_id=pago.id_pago, anulado_en=None
        ).first()

        pago.eliminado_en = ahora_utc()

        anulacion = AnulacionPago(
            id_pago=pago.id_pago,
            motivo=motivo.strip(),
        )
        db.session.add(anulacion)
        numero_recibo = f"{pago.id_pago:06d}"
        if mov:
            mov.anulado_en = ahora_utc()
            mov.motivo_anulacion = f"Pago #{numero_recibo} anulado: {motivo}"

        alumno_nombre = pago.alumno.nombre_completo if pago.alumno else f"Alumno #{pago.id_alumno}"
        alumno_codigo = pago.alumno.codigo_interno if pago.alumno else ""
        monto_pago = float(pago.monto)
        mes_pagado = pago.mes_pagado
        modo_pago = pago.modo_pago

        auditoria = Auditoria(
            modulo="Pagos",
            accion="Anular",
            entidad="Pago",
            id_entidad=pago.id_pago,
            id_usuario=id_usuario,
            valor_anterior=f"Recibo #{numero_recibo} | {alumno_nombre} ({alumno_codigo}) | Mes: {mes_pagado} | Bs. {monto_pago:.2f} ({modo_pago})",
            valor_nuevo=f"ANULADO | Motivo: {motivo}",
            detalle=f"Se anuló el Recibo #{numero_recibo} de {alumno_nombre} (Mes: {mes_pagado}, Bs. {monto_pago:.2f}, {modo_pago}). Motivo: {motivo}",
        )
        db.session.add(auditoria)
        db.session.commit()

        return pago
