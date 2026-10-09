"""Reglas de negocio centrales del sistema.

- Asignación automática de categoría según edad.
- Cálculo de fechas de vencimiento de mensualidad (por continuidad).
- Cálculo del "mes que se paga" siguiente disponible.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from app.extensions import db

from app.models import Categoria, Pago, Obligacion


def calcular_edad(fecha_nacimiento: date, referencia: date = None) -> int:
    referencia = referencia or date.today()
    años = referencia.year - fecha_nacimiento.year
    if (referencia.month, referencia.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        años -= 1
    return años


def categoria_automatica_por_edad(fecha_nacimiento: date):
    """Devuelve la Categoria cuyo rango de edad contiene la edad del alumno, o None."""
    edad = calcular_edad(fecha_nacimiento)
    categorias = Categoria.query.filter(
        Categoria.edad_min.isnot(None), Categoria.edad_max.isnot(None)
    ).all()
    for c in categorias:
        if c.edad_min <= edad <= c.edad_max:
            return c
    return None


def siguiente_mes_a_pagar(alumno):
    """Determina cuál es el próximo mes (YYYY-MM) que corresponde pagar,
    según el último pago registrado y por continuidad."""
    pendientes = Obligacion.query.filter_by(
        id_alumno=alumno.id_alumno, concepto="Mensualidad"
    ).order_by(Obligacion.periodo).all()
    pendiente = next((o for o in pendientes if o.saldo > 0), None)
    if pendiente:
        return pendiente.periodo
    consulta = Pago.query.filter_by(
        id_alumno=alumno.id_alumno, eliminado_en=None
    )
    if alumno.fecha_ultima_reactivacion:
        mes_reactivacion = alumno.fecha_ultima_reactivacion.strftime("%Y-%m")
        consulta = consulta.filter(Pago.mes_pagado >= mes_reactivacion)
    ultimo = consulta.order_by(Pago.fecha_vencimiento.desc()).first()
    if ultimo is None:
        # Un ciclo reactivado comienza en el mes de su nueva fecha base.
        base = alumno.fecha_ultima_reactivacion or date.today()
        return f"{base.year:04d}-{base.month:02d}"
    anio, mes = map(int, ultimo.mes_pagado.split("-"))
    siguiente = date(anio, mes, 1) + relativedelta(months=1)
    return f"{siguiente.year:04d}-{siguiente.month:02d}"


def calcular_vencimiento(alumno, fecha_pago: date, mes_pagado: str):
    """Calcula la fecha de vencimiento de un pago.

    - Si es el primer pago del alumno: vencimiento = fecha_base_pago (definida
      manualmente por el usuario, normalmente fecha_pago) + 1 mes.
    - Si ya existen pagos previos: se calcula por continuidad a partir de la
      fecha base original del alumno, sumando la cantidad de meses
      correspondiente al mes que se está pagando.
    """
    if alumno.fecha_base_pago is None:
        base = fecha_pago
    else:
        base = alumno.fecha_base_pago

    anio, mes = map(int, mes_pagado.split("-"))
    anio_base, mes_base = base.year, base.month
    meses_transcurridos = (anio - anio_base) * 12 + (mes - mes_base)
    vencimiento = base + relativedelta(months=meses_transcurridos + 1)
    return vencimiento


def ya_existe_pago_mes(alumno_id: int, mes_pagado: str) -> bool:
    return (
        Pago.query.filter_by(id_alumno=alumno_id, mes_pagado=mes_pagado, eliminado_en=None).first()
        is not None
    )


def calcular_monto_pago(alumno, es_beca_este_pago: bool, periodo: str = None):
    """Calcula el monto a cobrar según el monto de mensualidad configurado
    y el tipo de beca del alumno (Completa = 0, Media = 50%, Ninguna = 100%).
    Si el pago se marca manualmente como cubierto por beca, el monto es 0."""
    from app.models import Configuracion, Tarifa, BecaHistorial, InscripcionGestion

    referencia = date.today()
    if periodo:
        try:
            referencia = date(*map(int, periodo.split("-")), 1)
        except (TypeError, ValueError):
            pass
    inscripcion = InscripcionGestion.query.filter_by(
        id_alumno=alumno.id_alumno, gestion=referencia.year
    ).first()
    monto_base = None
    if inscripcion:
        monto_base = inscripcion.monto_tarifa
        if monto_base is None and inscripcion.tarifa:
            monto_base = inscripcion.tarifa.monto
    if monto_base is None:
        tarifa = Tarifa.query.filter(
            Tarifa.concepto == "Mensualidad", Tarifa.fecha_inicio <= referencia,
            db.or_(Tarifa.fecha_fin.is_(None), Tarifa.fecha_fin >= referencia),
            db.or_(Tarifa.id_categoria == alumno.id_categoria, Tarifa.id_categoria.is_(None)),
        ).order_by(Tarifa.id_categoria.desc(), Tarifa.fecha_inicio.desc()).first()
        monto_base = tarifa.monto if tarifa else Configuracion.obtener().monto_mensualidad
    historial = BecaHistorial.query.filter(
        BecaHistorial.id_alumno == alumno.id_alumno,
        BecaHistorial.fecha_inicio <= referencia,
        db.or_(BecaHistorial.fecha_fin.is_(None), BecaHistorial.fecha_fin >= referencia),
        BecaHistorial.estado == "Activa",
    ).order_by(BecaHistorial.fecha_inicio.desc(), BecaHistorial.id_beca.desc()).first()
    porcentaje = Decimal(str(historial.porcentaje if historial else (
        {"Ninguna": 0, "Media": 50, "Completa": 100}.get(alumno.beca_vigente, 0)
    )))
    if es_beca_este_pago:
        return Decimal("0.00")
    monto_base = Decimal(str(monto_base or 0))
    return (monto_base * (Decimal("100") - porcentaje) / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
