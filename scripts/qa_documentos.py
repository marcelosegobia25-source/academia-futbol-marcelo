"""Genera muestras de todos los documentos descargables para control visual."""
from pathlib import Path
from urllib.parse import urlencode

from app import create_app
from app.models import Alumno, Pago, Partido, Campeonato


SALIDA = Path("tmp") / "qa_documentos"


def guardar(respuesta, nombre):
    if respuesta.status_code != 200:
        raise RuntimeError(f"{nombre}: HTTP {respuesta.status_code}")
    ruta = SALIDA / nombre
    ruta.write_bytes(respuesta.data)
    print(f"{nombre}: {len(respuesta.data)} bytes")


app = create_app()
app.config["WTF_CSRF_ENABLED"] = False
SALIDA.mkdir(parents=True, exist_ok=True)

with app.app_context():
    alumno = Alumno.query.order_by(Alumno.id_alumno).first()
    pago = Pago.query.filter(Pago.eliminado_en.is_(None)).order_by(Pago.id_pago).first()
    partidos = Partido.query.order_by(Partido.fecha, Partido.id_partido).limit(12).all()
    campeonato = Campeonato.query.order_by(Campeonato.id_campeonato).first()
    if not alumno or not pago:
        raise RuntimeError("Se necesita al menos un alumno y un pago para la prueba.")

    cliente = app.test_client()
    columnas_alumnos = [
        "alumno", "ci", "categoria", "edad", "equipos", "posicion",
        "beca", "sexo", "campeonatos", "mensualidad", "estado", "telefono",
    ]
    columnas_pagos = [
        "id_pago", "alumno", "ci", "categoria", "mes", "fecha_pago",
        "hora", "vencimiento", "estado", "modo", "beca", "monto",
    ]
    comun = {"incluir_escudo": "1", "nombre_archivo": "Prueba visual completa"}

    consulta_alumnos = urlencode(
        {**comun, "columnas": columnas_alumnos}, doseq=True
    )
    consulta_pagos = urlencode(
        {**comun, "columnas": columnas_pagos}, doseq=True
    )
    consulta_resumen = urlencode(comun)

    guardar(cliente.get(f"/alumnos/exportar?{consulta_alumnos}"), "alumnos.xlsx")
    guardar(cliente.get(f"/alumnos/exportar.pdf?{consulta_alumnos}"), "alumnos.pdf")
    guardar(cliente.get(f"/pagos/exportar?{consulta_pagos}"), "pagos.xlsx")
    guardar(cliente.get(f"/pagos/exportar.pdf?{consulta_pagos}"), "pagos.pdf")
    guardar(cliente.get(f"/pagos/resumen-6-meses.xlsx?{consulta_resumen}"), "pagos_6_meses.xlsx")
    guardar(cliente.get(f"/pagos/resumen-6-meses.pdf?{consulta_resumen}"), "pagos_6_meses.pdf")
    guardar(cliente.get(f"/alumnos/{alumno.id_alumno}/ficha.pdf"), "ficha_alumno.pdf")
    guardar(cliente.get(f"/pagos/{pago.id_pago}/recibo.pdf"), "recibo_pago.pdf")

    guardar(
        cliente.post(
            "/partidos/convocatoria.pdf",
            data={"seleccionados": [str(partido.id_partido) for partido in partidos]},
        ),
        "convocatoria_partidos.pdf",
    )
    if campeonato:
        base_campeonato = f"/campeonatos/{campeonato.id_campeonato}"
        guardar(cliente.get(f"{base_campeonato}/fixture.xlsx"), "fixture_campeonato.xlsx")
        guardar(cliente.get(f"{base_campeonato}/fixture.pdf"), "fixture_campeonato.pdf")
        guardar(cliente.get(f"{base_campeonato}/posiciones.xlsx"), "posiciones_campeonato.xlsx")
        guardar(cliente.get(f"{base_campeonato}/posiciones.pdf"), "posiciones_campeonato.pdf")
