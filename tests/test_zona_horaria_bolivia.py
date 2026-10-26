"""Pruebas unitarias y de integración para la zona horaria de Bolivia (UTC-4)

Verifica que las marcas de tiempo almacenadas en UTC en la base de datos se conviertan
exactamente a la hora local boliviana (UTC-4) en funciones auxiliares y filtros Jinja2.
"""

from datetime import date, datetime, timedelta, timezone
from app.utils.tiempo import (
    ZONA_BOLIVIA,
    a_bolivia,
    ahora_bolivia,
    fecha_bo,
    fecha_hora_bo,
    hora_bo,
    hoy_bolivia,
)


def test_zona_bolivia_es_utc_menos_4():
    """Verifica que el desplazamiento de la zona horaria de Bolivia sea de -4 horas."""
    ahora = ahora_bolivia()
    assert ahora.tzinfo is not None
    assert ahora.utcoffset() == timedelta(hours=-4)


def test_hoy_bolivia_retorna_fecha():
    """Verifica que hoy_bolivia retorne un objeto date."""
    hoy = hoy_bolivia()
    assert isinstance(hoy, date)


def test_conversion_a_bolivia_desde_utc_naive():
    """Convierte naive UTC a datetime aware en UTC-4."""
    # 21:30 UTC corresponde a las 17:30 en Bolivia (4 horas menos)
    dt_utc = datetime(2026, 10, 26, 21, 30, 0)
    dt_bo = a_bolivia(dt_utc)

    assert dt_bo.tzinfo == ZONA_BOLIVIA
    assert dt_bo.hour == 17
    assert dt_bo.minute == 30
    assert dt_bo.day == 26


def test_conversion_a_bolivia_desde_utc_aware():
    """Convierte datetime aware con timezone.utc a UTC-4."""
    dt_utc = datetime(2026, 10, 26, 2, 15, 0, tzinfo=timezone.utc)
    # 02:15 UTC del 26 corresponde a las 22:15 del 25 en Bolivia
    dt_bo = a_bolivia(dt_utc)

    assert dt_bo.day == 25
    assert dt_bo.hour == 22
    assert dt_bo.minute == 15


def test_filtros_formato_bolivia():
    """Verifica los formateadores de fecha y hora para plantillas."""
    dt_utc = datetime(2026, 10, 26, 21, 45, 0)

    assert fecha_hora_bo(dt_utc) == "26/10/2026 17:45"
    assert fecha_bo(dt_utc) == "26/10/2026"
    assert hora_bo(dt_utc) == "17:45"
    assert fecha_hora_bo(None) == "—"
    assert fecha_bo(None) == "—"


def test_filtros_jinja_en_app_flask(app):
    """Verifica que los filtros estén registrados y operen dentro del contexto Jinja."""
    with app.app_context():
        from flask import render_template_string

        plantilla = (
            "{{ dt | fecha_hora_bo }} | {{ dt | fecha_bo }} | {{ dt | hora_bo }}"
        )
        dt_utc = datetime(2026, 10, 26, 23, 0, 0)

        resultado = render_template_string(plantilla, dt=dt_utc)
        assert resultado == "26/10/2026 19:00 | 26/10/2026 | 19:00"
