from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from app.extensions import db
from app.models import Pago, Alumno, Configuracion, Obligacion, AplicacionPago, MovimientoContable, Auditoria


class RegistrarPagoUseCase:
    """Caso de uso: Registro de cobro de mensualidad para un alumno."""

    def ejecutar(self, id_alumno, datos, id_usuario=None):
        alumno = Alumno.query.get_or_404(id_alumno)

        fecha_pago = datos.get("fecha_pago")
        if isinstance(fecha_pago, str):
            fecha_pago = datetime.strptime(fecha_pago, "%Y-%m-%d").date()
        fecha_pago = fecha_pago or date.today()

        modo_pago = datos.get("modo_pago", "Efectivo")
        mes_pagado = datos.get("mes_pagado")
        if not mes_pagado:
            mes_pagado = fecha_pago.strftime("%Y-%m")

        es_beca = bool(datos.get("es_beca", False))
        monto = Decimal(str(datos.get("monto", 0))) if not es_beca else Decimal("0.00")
        numero_operacion = datos.get("numero_operacion", "").strip() or None

        # Cálculo de vencimiento
        fecha_vencimiento = datos.get("fecha_vencimiento")
        if isinstance(fecha_vencimiento, str):
            fecha_vencimiento = datetime.strptime(fecha_vencimiento, "%Y-%m-%d").date()

        if not fecha_vencimiento:
            partes = mes_pagado.split("-")
            anio, mes = int(partes[0]), int(partes[1])
            dia_base = alumno.fecha_base_pago.day if alumno.fecha_base_pago else fecha_pago.day
            dia_limite = min(dia_base, 28)
            fecha_vencimiento = date(anio, mes, dia_limite) + relativedelta(months=1)

        pago = Pago(
            id_alumno=alumno.id_alumno,
            fecha_pago=fecha_pago,
            hora_registro=datetime.now().time(),
            fecha_vencimiento=fecha_vencimiento,
            mes_pagado=mes_pagado,
            modo_pago=modo_pago,
            monto=monto,
            es_beca=es_beca,
            numero_operacion=numero_operacion,
        )
        db.session.add(pago)
        db.session.flush()

        # Si el alumno no tenía fecha_base_pago, asignarla
        if not alumno.fecha_base_pago:
            alumno.fecha_base_pago = fecha_pago

        # Vincular a obligación del mes
        obligacion = Obligacion.query.filter_by(
            id_alumno=alumno.id_alumno, concepto="Mensualidad", periodo=mes_pagado
        ).first()

        if not obligacion:
            obligacion = Obligacion(
                id_alumno=alumno.id_alumno,
                concepto="Mensualidad",
                periodo=mes_pagado,
                monto_original=monto,
                fecha_vencimiento=fecha_vencimiento,
                cubierto_beca=es_beca,
            )
            db.session.add(obligacion)
            db.session.flush()

        aplicacion = AplicacionPago(
            id_obligacion=obligacion.id_obligacion,
            id_pago=pago.id_pago,
            monto=monto,
        )
        db.session.add(aplicacion)

        # Registrar movimiento contable
        if monto > 0:
            mov = MovimientoContable(
                tipo="Ingreso",
                categoria="Mensualidades",
                concepto=f"Pago mensualidad {mes_pagado} - {alumno.nombre_completo}",
                monto=monto,
                fecha=fecha_pago,
                modo_pago=modo_pago,
                numero_operacion=numero_operacion,
                origen_tipo="Pago",
                origen_id=pago.id_pago,
            )
            db.session.add(mov)

        auditoria = Auditoria(
            modulo="Pagos",
            accion="Registrar pago",
            entidad="Pago",
            id_entidad=pago.id_pago,
            detalle=f"Cobro mensualidad {mes_pagado} de {alumno.nombre_completo}: Bs. {monto} ({modo_pago})",
            id_usuario=id_usuario,
            valor_nuevo=f"Bs. {monto}",
        )
        db.session.add(auditoria)
        db.session.commit()

        return pago
