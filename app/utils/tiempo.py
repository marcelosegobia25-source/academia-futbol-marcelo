"""Utilidades de fecha, hora y zona horaria para Bolivia (UTC-4).

Bolivia no utiliza horario de verano (DST), manteniéndose permanentemente en UTC-4.
Este módulo centraliza la conversión de fechas UTC almacenadas en la base de datos
hacia la hora local boliviana y viceversa, garantizando uniformidad en auditoría,
cierres de caja, reportes y vistas del sistema.
"""

from datetime import date, datetime, timedelta, timezone

# Zona horaria oficial de Bolivia: UTC - 4 horas sin DST
ZONA_BOLIVIA = timezone(timedelta(hours=-4))


def ahora_bolivia() -> datetime:
    """Retorna el instante actual en hora de Bolivia (con información de zona horaria)."""
    return datetime.now(ZONA_BOLIVIA)


def hoy_bolivia() -> date:
    """Retorna la fecha calendario actual en Bolivia.

    Previene que despliegues en servidores con reloj UTC (como Render, Vercel o AWS)
    cambien de día a las 20:00 (8:00 PM) hora boliviana.
    """
    return ahora_bolivia().date()


def a_bolivia(dt):
    """Convierte un objeto datetime (naive UTC o con tzinfo) a hora local de Bolivia.

    Si recibe un objeto `date` puro o `None`, lo retorna intacto.
    """
    if dt is None:
        return None
    if isinstance(dt, datetime):
        # Si no tiene zona horaria definida, proviene de la BD donde se guarda en UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZONA_BOLIVIA)
    return dt


def fecha_hora_bo(dt, formato: str = "%d/%m/%Y %H:%M") -> str:
    """Filtro Jinja: Formatea un datetime UTC a la hora local de Bolivia."""
    if not dt:
        return "—"
    convertido = a_bolivia(dt)
    if hasattr(convertido, "strftime"):
        return convertido.strftime(formato)
    return str(convertido)


def fecha_bo(dt, formato: str = "%d/%m/%Y") -> str:
    """Filtro Jinja: Formatea una fecha o datetime a DD/MM/AAAA."""
    if not dt:
        return "—"
    convertido = a_bolivia(dt)
    if hasattr(convertido, "strftime"):
        return convertido.strftime(formato)
    return str(convertido)


def hora_bo(dt, formato: str = "%H:%M") -> str:
    """Filtro Jinja: Formatea la hora HH:MM ajustada a Bolivia si es datetime."""
    if not dt:
        return "—"
    convertido = a_bolivia(dt)
    if hasattr(convertido, "strftime"):
        return convertido.strftime(formato)
    return str(convertido)
