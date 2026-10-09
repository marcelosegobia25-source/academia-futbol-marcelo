import re
from datetime import date, datetime


class ErrorValidacion(ValueError):
    pass


def texto_requerido(valor, campo, maximo=160):
    texto = (valor or "").strip()
    if not texto:
        raise ErrorValidacion(f"{campo} es obligatorio.")
    if len(texto) > maximo:
        raise ErrorValidacion(f"{campo} supera el máximo de {maximo} caracteres.")
    return texto


def texto_opcional(valor, campo, maximo=255):
    texto = (valor or "").strip()
    if not texto:
        return None
    if len(texto) > maximo:
        raise ErrorValidacion(f"{campo} supera el máximo de {maximo} caracteres.")
    return texto


def fecha_iso(valor, campo, requerida=True):
    if not valor:
        if requerida:
            raise ErrorValidacion(f"{campo} es obligatoria.")
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ErrorValidacion(f"{campo} no tiene una fecha válida.")


def hora_hm(valor, campo, requerida=False):
    if not valor:
        if requerida:
            raise ErrorValidacion(f"{campo} es obligatoria.")
        return None
    try:
        return datetime.strptime(valor, "%H:%M").time()
    except (TypeError, ValueError):
        raise ErrorValidacion(f"{campo} no tiene una hora válida.")


def mes_iso(valor):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", valor or ""):
        raise ErrorValidacion("El mes pagado no tiene un formato válido.")
    return valor


def entero(valor, campo, minimo=None, maximo=None, requerido=False):
    if valor in (None, ""):
        if requerido:
            raise ErrorValidacion(f"{campo} es obligatorio.")
        return None
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ErrorValidacion(f"{campo} debe ser un número entero.")
    if minimo is not None and numero < minimo:
        raise ErrorValidacion(f"{campo} no puede ser menor que {minimo}.")
    if maximo is not None and numero > maximo:
        raise ErrorValidacion(f"{campo} no puede ser mayor que {maximo}.")
    return numero


def decimal_positivo(valor, campo, maximo=None):
    if valor in (None, ""):
        return None
    try:
        numero = round(float(valor), 2)
    except (TypeError, ValueError):
        raise ErrorValidacion(f"{campo} debe ser un número válido.")
    if numero <= 0:
        raise ErrorValidacion(f"{campo} debe ser mayor que cero.")
    if maximo is not None and numero > maximo:
        raise ErrorValidacion(f"{campo} supera el máximo permitido.")
    return numero


def opcion(valor, permitidas, campo, opcional=False):
    if opcional and not valor:
        return None
    if valor not in permitidas:
        raise ErrorValidacion(f"{campo} contiene un valor no permitido.")
    return valor


def rango_fechas(inicio, fin, inicio_nombre="Fecha inicial", fin_nombre="Fecha final"):
    if fin and inicio and fin < inicio:
        raise ErrorValidacion(f"{fin_nombre} no puede ser anterior a {inicio_nombre}.")


def fecha_no_futura(fecha, campo):
    if fecha > date.today():
        raise ErrorValidacion(f"{campo} no puede estar en el futuro.")
    return fecha
