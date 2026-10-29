"""Diagnóstico de integridad SQLite sin modificar información del usuario."""

import sqlite3
from pathlib import Path


def _identificador(nombre):
    return '"' + str(nombre).replace('"', '""') + '"'


COMPROBACIONES_LOGICAS = [
    ("Pagos con monto negativo", "SELECT COUNT(*) FROM pago WHERE monto < 0"),
    ("Aplicaciones que superan el total de la obligación", "SELECT COUNT(*) FROM obligacion o WHERE (SELECT COALESCE(SUM(a.monto),0) FROM aplicacion_pago a JOIN pago p ON p.id_pago=a.id_pago WHERE a.id_obligacion=o.id_obligacion AND p.eliminado_en IS NULL) > (o.monto_original-o.descuento+o.recargo)+0.01"),
    ("Pagos activos sin aplicación", "SELECT COUNT(*) FROM pago p LEFT JOIN aplicacion_pago a ON a.id_pago=p.id_pago WHERE p.eliminado_en IS NULL AND a.id_pago IS NULL"),
    ("Posibles partidos duplicados", "SELECT COUNT(*) FROM (SELECT fecha,hora,id_equipo,COALESCE(id_equipo_rival,-1),lower(trim(rival)),COALESCE(id_campeonato,-1),COALESCE(id_categoria,-1),COALESCE(id_lugar,-1) FROM partido GROUP BY fecha,hora,id_equipo,COALESCE(id_equipo_rival,-1),lower(trim(rival)),COALESCE(id_campeonato,-1),COALESCE(id_categoria,-1),COALESCE(id_lugar,-1) HAVING COUNT(*)>1) AS subconsulta_duplicados"),
    ("Partidos sin proyección en Agenda", "SELECT COUNT(*) FROM partido p LEFT JOIN evento_agenda e ON e.id_partido=p.id_partido WHERE e.id_evento IS NULL"),
    ("Eventos de partido huérfanos", "SELECT COUNT(*) FROM evento_agenda e LEFT JOIN partido p ON p.id_partido=e.id_partido WHERE e.tipo='Partido' AND p.id_partido IS NULL"),
    ("Proyecciones de partido desincronizadas", "SELECT COUNT(*) FROM evento_agenda e JOIN partido p ON p.id_partido=e.id_partido WHERE e.fecha<>p.fecha OR COALESCE(CAST(e.hora AS VARCHAR),'')<>COALESCE(CAST(p.hora AS VARCHAR),'') OR COALESCE(e.id_lugar,-1)<>COALESCE(p.id_lugar,-1) OR COALESCE(e.id_equipo,-1)<>COALESCE(p.id_equipo,-1)"),
]


def auditar_base_datos(session, nombre_motor="PostgreSQL"):
    """Ejecuta la auditoría lógica en cualquier motor relacional (ej. PostgreSQL / Supabase)."""
    from sqlalchemy import text
    resultado = {
        "ruta": nombre_motor, "existe": True, "integridad": "ok",
        "tablas": [], "sin_pk": [], "fks_invalidas": [], "alertas": [],
        "indices_recomendados": [], "estadisticas": {}, "duplicados_partidos": [],
    }
    for etiqueta, consulta in COMPROBACIONES_LOGICAS:
        try:
            cantidad = session.execute(text(consulta)).scalar() or 0
        except Exception:
            session.rollback()
            continue
        if cantidad:
            resultado["alertas"].append(f"{etiqueta}: {cantidad}")
    resultado["correcta"] = len(resultado["alertas"]) == 0
    return resultado


def auditar_sqlite(ruta):
    ruta = Path(ruta)
    resultado = {
        "ruta": str(ruta), "existe": ruta.is_file(), "integridad": "no ejecutada",
        "tablas": [], "sin_pk": [], "fks_invalidas": [], "alertas": [],
        "indices_recomendados": [], "estadisticas": {}, "duplicados_partidos": [],
    }
    if not ruta.is_file():
        resultado["alertas"].append("No se encontró el archivo de base de datos.")
        return resultado

    conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True, timeout=10)
    conexion.row_factory = sqlite3.Row
    try:
        resultado["integridad"] = conexion.execute("PRAGMA integrity_check").fetchone()[0]
        tablas = [fila[0] for fila in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        resultado["tablas"] = tablas
        for tabla in tablas:
            tabla_sql = _identificador(tabla)
            columnas = conexion.execute(f"PRAGMA table_info({tabla_sql})").fetchall()
            if not any(columna[5] for columna in columnas):
                resultado["sin_pk"].append(tabla)
            resultado["estadisticas"][tabla] = conexion.execute(
                f"SELECT COUNT(*) FROM {tabla_sql}"
            ).fetchone()[0]
            indices = conexion.execute(f"PRAGMA index_list({tabla_sql})").fetchall()
            columnas_indexadas = set()
            for indice in indices:
                columnas_indexadas.update(
                    fila[2] for fila in conexion.execute(f"PRAGMA index_info({_identificador(indice[1])})")
                )
            for fk in conexion.execute(f"PRAGMA foreign_key_list({tabla_sql})"):
                if fk[3] not in columnas_indexadas:
                    resultado["indices_recomendados"].append(f"{tabla}.{fk[3]}")

        resultado["fks_invalidas"] = [dict(fila) for fila in conexion.execute("PRAGMA foreign_key_check")]
        if "partido" in tablas:
            resultado["duplicados_partidos"] = [dict(fila) for fila in conexion.execute("""
                SELECT GROUP_CONCAT(id_partido) ids, fecha, hora, id_equipo, id_equipo_rival,
                       id_campeonato, id_categoria, id_lugar, COUNT(*) cantidad
                FROM partido GROUP BY fecha,hora,id_equipo,COALESCE(id_equipo_rival,-1),
                     lower(trim(rival)),COALESCE(id_campeonato,-1),COALESCE(id_categoria,-1),COALESCE(id_lugar,-1)
                HAVING COUNT(*)>1 ORDER BY fecha,hora
            """)]

        for etiqueta, consulta in COMPROBACIONES_LOGICAS:
            try:
                cantidad = conexion.execute(consulta).fetchone()[0]
            except sqlite3.OperationalError:
                continue
            if cantidad:
                resultado["alertas"].append(f"{etiqueta}: {cantidad}")
    finally:
        conexion.close()
    resultado["correcta"] = (
        resultado["integridad"] == "ok" and not resultado["sin_pk"]
        and not resultado["fks_invalidas"] and not resultado["alertas"]
    )
    return resultado
