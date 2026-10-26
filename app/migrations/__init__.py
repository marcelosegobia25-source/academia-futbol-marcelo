"""Migraciones internas, versionadas e idempotentes para instalaciones locales.

Se mantienen dentro del proyecto para actualizar bases existentes sin borrar
datos. Cada migración se ejecuta una sola vez y queda registrada.
"""
from datetime import datetime, timezone

from sqlalchemy import inspect, text

from app.extensions import db


def _columnas(tabla):
    return {columna["name"] for columna in inspect(db.engine).get_columns(tabla)}


def _versiones_aplicadas():
    db.session.execute(text(
        "CREATE TABLE IF NOT EXISTS schema_migration ("
        "version INTEGER PRIMARY KEY, nombre VARCHAR(160) NOT NULL, "
        "aplicada_en TIMESTAMP NOT NULL)"
    ))
    db.session.commit()
    return {
        fila[0]
        for fila in db.session.execute(text("SELECT version FROM schema_migration")).all()
    }


def _registrar(version, nombre):
    db.session.execute(
        text(
            "INSERT INTO schema_migration(version, nombre, aplicada_en) "
            "VALUES (:version, :nombre, :aplicada_en)"
        ),
        {
            "version": version,
            "nombre": nombre,
            "aplicada_en": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )
    db.session.commit()


def _migracion_1_indices_integridad():
    db.session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_activo_mes "
        "ON pago(id_alumno, mes_pagado) WHERE eliminado_en IS NULL"
    ))
    db.session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_posicion_campeonato_categoria_equipo "
        "ON posicion(id_campeonato, id_categoria, id_equipo)"
    ))
    db.session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_alumno_ci "
        "ON alumno(ci) WHERE ci IS NOT NULL AND trim(ci) <> ''"
    ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_pago_alumno_vencimiento "
        "ON pago(id_alumno, fecha_vencimiento)"
    ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_partido_fecha ON partido(fecha)"
    ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_evento_agenda_fecha ON evento_agenda(fecha)"
    ))
    db.session.commit()


def _migracion_2_equipo_rival():
    if "id_equipo_rival" not in _columnas("partido"):
        db.session.execute(text(
            "ALTER TABLE partido ADD COLUMN id_equipo_rival INTEGER"
        ))
    db.session.execute(text(
        "UPDATE partido SET id_equipo_rival = ("
        "SELECT e.id_equipo FROM equipo e "
        "WHERE lower(trim(e.nombre)) = lower(trim(partido.rival)) "
        "AND e.id_categoria = partido.id_categoria LIMIT 1"
        ") WHERE id_equipo_rival IS NULL AND id_campeonato IS NOT NULL"
    ))
    db.session.execute(text(
        "UPDATE partido SET id_equipo_rival = ("
        "SELECT e.id_equipo FROM equipo e "
        "WHERE lower(trim(e.nombre)) = lower(trim(partido.rival)) LIMIT 1"
        ") WHERE id_equipo_rival IS NULL AND id_campeonato IS NOT NULL"
    ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_partido_equipo_rival "
        "ON partido(id_equipo_rival)"
    ))
    # SQLite no permite agregar una FK con ALTER TABLE; estos triggers
    # protegen la nueva relación en bases existentes.
    db.session.execute(text(
        "CREATE TRIGGER IF NOT EXISTS fk_partido_equipo_rival_insert "
        "BEFORE INSERT ON partido WHEN NEW.id_equipo_rival IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM equipo WHERE id_equipo = NEW.id_equipo_rival) "
        "BEGIN SELECT RAISE(ABORT, 'equipo rival inexistente'); END"
    ))
    db.session.execute(text(
        "CREATE TRIGGER IF NOT EXISTS fk_partido_equipo_rival_update "
        "BEFORE UPDATE OF id_equipo_rival ON partido WHEN NEW.id_equipo_rival IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM equipo WHERE id_equipo = NEW.id_equipo_rival) "
        "BEGIN SELECT RAISE(ABORT, 'equipo rival inexistente'); END"
    ))
    db.session.commit()


def _migracion_3_reparar_agenda():
    db.session.execute(text(
        "DELETE FROM evento_agenda WHERE id_partido IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM partido p WHERE p.id_partido = evento_agenda.id_partido)"
    ))
    db.session.execute(text(
        "INSERT INTO evento_agenda "
        "(hora, fecha, descripcion, lugar, id_categoria, id_equipo, tipo, id_partido) "
        "SELECT p.hora, p.fecha, 'Partido vs ' || p.rival, p.cancha, "
        "p.id_categoria, p.id_equipo, 'Partido', p.id_partido "
        "FROM partido p "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM evento_agenda e WHERE e.id_partido = p.id_partido"
        ")"
    ))
    db.session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_evento_agenda_partido "
        "ON evento_agenda(id_partido) WHERE id_partido IS NOT NULL"
    ))
    db.session.commit()


def _migracion_4_recalcular_posiciones():
    db.session.execute(text(
        "UPDATE posicion SET pj=0, pg=0, pe=0, pp=0, gf=0, gc=0"
    ))
    partidos = db.session.execute(text(
        "SELECT id_campeonato, id_categoria, id_equipo, id_equipo_rival, resultado "
        "FROM partido WHERE id_campeonato IS NOT NULL AND resultado IS NOT NULL"
    )).all()
    for campeonato, categoria, local, visita, resultado in partidos:
        if not visita or "-" not in resultado:
            continue
        try:
            goles_local, goles_visita = [int(valor) for valor in resultado.split("-", 1)]
        except ValueError:
            continue
        for equipo, favor, contra in (
            (local, goles_local, goles_visita),
            (visita, goles_visita, goles_local),
        ):
            if favor > contra:
                ganado, empatado, perdido = 1, 0, 0
            elif favor == contra:
                ganado, empatado, perdido = 0, 1, 0
            else:
                ganado, empatado, perdido = 0, 0, 1
            db.session.execute(text(
                "UPDATE posicion SET pj=pj+1, pg=pg+:pg, pe=pe+:pe, pp=pp+:pp, "
                "gf=gf+:gf, gc=gc+:gc WHERE id_campeonato=:campeonato "
                "AND id_categoria=:categoria AND id_equipo=:equipo"
            ), {
                "pg": ganado, "pe": empatado, "pp": perdido,
                "gf": favor, "gc": contra, "campeonato": campeonato,
                "categoria": categoria, "equipo": equipo,
            })
    db.session.commit()


def _migracion_5_equipos_rivales():
    if "es_rival" not in _columnas("equipo"):
        db.session.execute(text(
            "ALTER TABLE equipo ADD COLUMN es_rival BOOLEAN NOT NULL DEFAULT 0"
        ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_equipo_tipo_categoria "
        "ON equipo(es_rival, id_categoria, nombre)"
    ))
    db.session.commit()


def _migracion_6_catalogo_lugares():
    db.session.execute(text(
        "CREATE TABLE IF NOT EXISTS lugar ("
        "id_lugar INTEGER PRIMARY KEY, nombre VARCHAR(150) NOT NULL UNIQUE, "
        "tipo VARCHAR(20) NOT NULL DEFAULT 'Cancha', "
        "direccion VARCHAR(255), activo BOOLEAN NOT NULL DEFAULT 1)"
    ))
    fuentes = [
        ("partido", "cancha", "Cancha"),
        ("campeonato", "lugar", "Lugar"),
        ("evento_agenda", "lugar", "Lugar"),
        ("entrenamiento", "lugar", "Cancha"),
    ]
    for tabla, columna, tipo in fuentes:
        db.session.execute(text(
            f"INSERT OR IGNORE INTO lugar(nombre, tipo, activo) "
            f"SELECT DISTINCT trim({columna}), :tipo, 1 FROM {tabla} "
            f"WHERE {columna} IS NOT NULL AND trim({columna}) <> ''"
        ), {"tipo": tipo})
    db.session.commit()


def _migracion_7_campeonatos_avanzados():
    columnas_campeonato = {
        "formato": "VARCHAR(30) NOT NULL DEFAULT 'Liga'",
        "vueltas": "INTEGER NOT NULL DEFAULT 1",
        "clasificados": "INTEGER NOT NULL DEFAULT 4",
        "puntos_victoria": "INTEGER NOT NULL DEFAULT 3",
        "puntos_empate": "INTEGER NOT NULL DEFAULT 1",
        "puntos_derrota": "INTEGER NOT NULL DEFAULT 0",
        "tercer_puesto": "BOOLEAN NOT NULL DEFAULT 0",
        "finalizado_en": "DATETIME",
        "motivo_cierre": "VARCHAR(255)",
    }
    existentes = _columnas("campeonato")
    for nombre, definicion in columnas_campeonato.items():
        if nombre not in existentes:
            db.session.execute(text(
                f"ALTER TABLE campeonato ADD COLUMN {nombre} {definicion}"
            ))

    columnas_partido = {
        "fase": "VARCHAR(30) NOT NULL DEFAULT 'Liga'",
        "grupo": "VARCHAR(30)",
        "jornada": "INTEGER",
        "orden_llave": "INTEGER",
        "estado_partido": "VARCHAR(20) NOT NULL DEFAULT 'Programado'",
        "goles_local": "INTEGER",
        "goles_visita": "INTEGER",
        "penales_local": "INTEGER",
        "penales_visita": "INTEGER",
        "observacion": "VARCHAR(255)",
        "id_partido_origen_local": "INTEGER",
        "id_partido_origen_visita": "INTEGER",
    }
    existentes = _columnas("partido")
    for nombre, definicion in columnas_partido.items():
        if nombre not in existentes:
            db.session.execute(text(
                f"ALTER TABLE partido ADD COLUMN {nombre} {definicion}"
            ))
    db.session.execute(text(
        "UPDATE partido SET "
        "goles_local = CAST(substr(resultado, 1, instr(resultado, '-') - 1) AS INTEGER), "
        "goles_visita = CAST(substr(resultado, instr(resultado, '-') + 1) AS INTEGER), "
        "estado_partido = 'Finalizado' "
        "WHERE resultado IS NOT NULL AND instr(resultado, '-') > 0 "
        "AND goles_local IS NULL AND goles_visita IS NULL"
    ))

    existentes = _columnas("alumno_campeonato")
    if "archivado" not in existentes:
        db.session.execute(text(
            "ALTER TABLE alumno_campeonato ADD COLUMN archivado BOOLEAN NOT NULL DEFAULT 0"
        ))
    if "archivado_en" not in existentes:
        db.session.execute(text(
            "ALTER TABLE alumno_campeonato ADD COLUMN archivado_en DATETIME"
        ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_partido_campeonato_fase_jornada "
        "ON partido(id_campeonato, id_categoria, fase, jornada)"
    ))
    db.session.commit()


def _migracion_8_integridad_auditoria_y_caja():
    if "numero_operacion" not in _columnas("pago"):
        db.session.execute(text(
            "ALTER TABLE pago ADD COLUMN numero_operacion VARCHAR(80)"
        ))

    db.session.execute(text(
        "CREATE TABLE IF NOT EXISTS anulacion_pago ("
        "id_anulacion INTEGER PRIMARY KEY, id_pago INTEGER NOT NULL UNIQUE, "
        "motivo VARCHAR(255) NOT NULL, creado_en DATETIME NOT NULL, "
        "id_pago_reemplazo INTEGER, "
        "FOREIGN KEY(id_pago) REFERENCES pago(id_pago) ON DELETE RESTRICT, "
        "FOREIGN KEY(id_pago_reemplazo) REFERENCES pago(id_pago) ON DELETE SET NULL)"
    ))
    db.session.execute(text(
        "CREATE TABLE IF NOT EXISTS cierre_caja ("
        "id_cierre INTEGER PRIMARY KEY, fecha DATE NOT NULL UNIQUE, "
        "efectivo_sistema NUMERIC(12,2) NOT NULL DEFAULT 0, "
        "qr_sistema NUMERIC(12,2) NOT NULL DEFAULT 0, "
        "efectivo_contado NUMERIC(12,2) NOT NULL DEFAULT 0, "
        "qr_confirmado NUMERIC(12,2) NOT NULL DEFAULT 0, "
        "diferencia NUMERIC(12,2) NOT NULL DEFAULT 0, "
        "observacion VARCHAR(255), cerrado_en DATETIME NOT NULL)"
    ))
    db.session.execute(text(
        "CREATE TABLE IF NOT EXISTS historial_alumno ("
        "id_historial INTEGER PRIMARY KEY, id_alumno INTEGER NOT NULL, "
        "tipo VARCHAR(40) NOT NULL, valor_anterior TEXT, valor_nuevo TEXT, "
        "motivo VARCHAR(255), creado_en DATETIME NOT NULL, "
        "FOREIGN KEY(id_alumno) REFERENCES alumno(id_alumno) ON DELETE CASCADE)"
    ))
    db.session.execute(text(
        "CREATE TABLE IF NOT EXISTS auditoria ("
        "id_auditoria INTEGER PRIMARY KEY, modulo VARCHAR(40) NOT NULL, "
        "accion VARCHAR(60) NOT NULL, entidad VARCHAR(40), id_entidad INTEGER, "
        "detalle TEXT, creado_en DATETIME NOT NULL)"
    ))
    db.session.execute(text(
        "CREATE TABLE IF NOT EXISTS campeonato_categoria_config ("
        "id INTEGER PRIMARY KEY, id_campeonato INTEGER NOT NULL, "
        "id_categoria INTEGER NOT NULL, formato VARCHAR(30) NOT NULL DEFAULT 'Liga', "
        "vueltas INTEGER NOT NULL DEFAULT 1, clasificados INTEGER NOT NULL DEFAULT 4, "
        "tercer_puesto BOOLEAN NOT NULL DEFAULT 0, "
        "UNIQUE(id_campeonato,id_categoria), "
        "FOREIGN KEY(id_campeonato) REFERENCES campeonato(id_campeonato) ON DELETE CASCADE, "
        "FOREIGN KEY(id_categoria) REFERENCES categoria(id_categoria) ON DELETE RESTRICT)"
    ))
    db.session.execute(text(
        "CREATE TABLE IF NOT EXISTS podio_campeonato ("
        "id INTEGER PRIMARY KEY, id_campeonato INTEGER NOT NULL, "
        "id_categoria INTEGER NOT NULL, id_campeon INTEGER, id_subcampeon INTEGER, "
        "id_tercero INTEGER, registrado_en DATETIME NOT NULL, "
        "UNIQUE(id_campeonato,id_categoria), "
        "FOREIGN KEY(id_campeonato) REFERENCES campeonato(id_campeonato) ON DELETE CASCADE, "
        "FOREIGN KEY(id_categoria) REFERENCES categoria(id_categoria) ON DELETE RESTRICT, "
        "FOREIGN KEY(id_campeon) REFERENCES equipo(id_equipo) ON DELETE RESTRICT, "
        "FOREIGN KEY(id_subcampeon) REFERENCES equipo(id_equipo) ON DELETE RESTRICT, "
        "FOREIGN KEY(id_tercero) REFERENCES equipo(id_equipo) ON DELETE RESTRICT)"
    ))
    db.session.execute(text(
        "INSERT OR IGNORE INTO campeonato_categoria_config "
        "(id_campeonato,id_categoria,formato,vueltas,clasificados,tercer_puesto) "
        "SELECT cc.id_campeonato,cc.id_categoria,c.formato,c.vueltas,c.clasificados,c.tercer_puesto "
        "FROM campeonato_categoria cc JOIN campeonato c "
        "ON c.id_campeonato=cc.id_campeonato"
    ))

    disparadores = [
        ("ck_partido_insert", "BEFORE INSERT ON partido", """
            WHEN NEW.id_equipo_rival IS NOT NULL AND NEW.id_equipo = NEW.id_equipo_rival
            BEGIN SELECT RAISE(ABORT, 'local y visitante deben ser distintos'); END
        """),
        ("ck_partido_update", "BEFORE UPDATE ON partido", """
            WHEN NEW.id_equipo_rival IS NOT NULL AND NEW.id_equipo = NEW.id_equipo_rival
            BEGIN SELECT RAISE(ABORT, 'local y visitante deben ser distintos'); END
        """),
        ("ck_partido_valores_insert", "BEFORE INSERT ON partido", """
            WHEN coalesce(NEW.goles_local,0)<0 OR coalesce(NEW.goles_visita,0)<0
              OR coalesce(NEW.penales_local,0)<0 OR coalesce(NEW.penales_visita,0)<0
              OR NEW.fase NOT IN ('Liga','Grupos','Cuartos','Semifinal','Final','Tercer puesto')
              OR NEW.estado_partido NOT IN ('Programado','Finalizado','Suspendido','Reprogramado','Cancelado','Walkover')
            BEGIN SELECT RAISE(ABORT, 'valores de partido invalidos'); END
        """),
        ("ck_partido_valores_update", "BEFORE UPDATE ON partido", """
            WHEN coalesce(NEW.goles_local,0)<0 OR coalesce(NEW.goles_visita,0)<0
              OR coalesce(NEW.penales_local,0)<0 OR coalesce(NEW.penales_visita,0)<0
              OR NEW.fase NOT IN ('Liga','Grupos','Cuartos','Semifinal','Final','Tercer puesto')
              OR NEW.estado_partido NOT IN ('Programado','Finalizado','Suspendido','Reprogramado','Cancelado','Walkover')
            BEGIN SELECT RAISE(ABORT, 'valores de partido invalidos'); END
        """),
        ("ck_campeonato_insert", "BEFORE INSERT ON campeonato", """
            WHEN NEW.estado NOT IN ('Borrador','Planificado','En curso','Finalizado','Cancelado')
              OR NEW.formato NOT IN ('Liga','Eliminación directa','Liga + eliminatorias','Manual')
              OR NEW.vueltas NOT IN (1,2) OR NEW.clasificados NOT IN (2,4,8)
            BEGIN SELECT RAISE(ABORT, 'configuracion de campeonato invalida'); END
        """),
        ("ck_campeonato_update", "BEFORE UPDATE ON campeonato", """
            WHEN NEW.estado NOT IN ('Borrador','Planificado','En curso','Finalizado','Cancelado')
              OR NEW.formato NOT IN ('Liga','Eliminación directa','Liga + eliminatorias','Manual')
              OR NEW.vueltas NOT IN (1,2) OR NEW.clasificados NOT IN (2,4,8)
            BEGIN SELECT RAISE(ABORT, 'configuracion de campeonato invalida'); END
        """),
        ("uq_equipo_insert", "BEFORE INSERT ON equipo", """
            WHEN EXISTS (SELECT 1 FROM equipo e
              WHERE lower(trim(e.nombre))=lower(trim(NEW.nombre))
              AND coalesce(e.id_categoria,-1)=coalesce(NEW.id_categoria,-1)
              AND e.es_rival=NEW.es_rival)
            BEGIN SELECT RAISE(ABORT, 'equipo duplicado en la categoria'); END
        """),
        ("uq_equipo_update", "BEFORE UPDATE OF nombre,id_categoria,es_rival ON equipo", """
            WHEN EXISTS (SELECT 1 FROM equipo e
              WHERE e.id_equipo<>NEW.id_equipo
              AND lower(trim(e.nombre))=lower(trim(NEW.nombre))
              AND coalesce(e.id_categoria,-1)=coalesce(NEW.id_categoria,-1)
              AND e.es_rival=NEW.es_rival)
            BEGIN SELECT RAISE(ABORT, 'equipo duplicado en la categoria'); END
        """),
        ("ck_categoria_solape_insert", "BEFORE INSERT ON categoria", """
            WHEN NEW.edad_min IS NOT NULL AND NEW.edad_max IS NOT NULL AND EXISTS (
              SELECT 1 FROM categoria c WHERE c.edad_min IS NOT NULL AND c.edad_max IS NOT NULL
              AND NEW.edad_min<=c.edad_max AND NEW.edad_max>=c.edad_min)
            BEGIN SELECT RAISE(ABORT, 'rango de edad solapado'); END
        """),
        ("ck_categoria_solape_update", "BEFORE UPDATE OF edad_min,edad_max ON categoria", """
            WHEN NEW.edad_min IS NOT NULL AND NEW.edad_max IS NOT NULL AND EXISTS (
              SELECT 1 FROM categoria c WHERE c.id_categoria<>NEW.id_categoria
              AND c.edad_min IS NOT NULL AND c.edad_max IS NOT NULL
              AND NEW.edad_min<=c.edad_max AND NEW.edad_max>=c.edad_min)
            BEGIN SELECT RAISE(ABORT, 'rango de edad solapado'); END
        """),
    ]
    for nombre, evento, cuerpo in disparadores:
        db.session.execute(text(
            f"CREATE TRIGGER IF NOT EXISTS {nombre} {evento} {cuerpo}"
        ))

    indices = [
        "CREATE INDEX IF NOT EXISTS ix_pago_mes_activo ON pago(mes_pagado, eliminado_en)",
        "CREATE INDEX IF NOT EXISTS ix_pago_fecha_modo ON pago(fecha_pago, modo_pago, eliminado_en)",
        "CREATE INDEX IF NOT EXISTS ix_alumno_estado_categoria ON alumno(estado, id_categoria)",
        "CREATE INDEX IF NOT EXISTS ix_alumno_nombre_apellido ON alumno(apellido, nombre)",
        "CREATE INDEX IF NOT EXISTS ix_auditoria_modulo_fecha ON auditoria(modulo, creado_en)",
        "CREATE INDEX IF NOT EXISTS ix_historial_alumno_fecha ON historial_alumno(id_alumno, creado_en)",
        "CREATE INDEX IF NOT EXISTS ix_partido_campeonato_estado ON partido(id_campeonato, estado_partido)",
    ]
    for sentencia in indices:
        db.session.execute(text(sentencia))
    db.session.commit()


def _migracion_9_reactivacion_alumnos():
    """Abre ciclos de mensualidad sin alterar los pagos históricos."""
    if "fecha_ultima_reactivacion" not in _columnas("alumno"):
        db.session.execute(text(
            "ALTER TABLE alumno ADD COLUMN fecha_ultima_reactivacion DATE"
        ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_alumno_reactivacion "
        "ON alumno(fecha_ultima_reactivacion)"
    ))
    db.session.commit()


def _migracion_10_endurecimiento_operativo():
    columnas_por_tabla = {
        "configuracion": [
            ("nombre_academia", "VARCHAR(150) NOT NULL DEFAULT 'Mi Academia Deportiva'"),
            ("telefono", "VARCHAR(50)"), ("direccion", "VARCHAR(255)"),
            ("moneda", "VARCHAR(10) NOT NULL DEFAULT 'BOB'"),
            ("dias_proximo_vencimiento", "INTEGER NOT NULL DEFAULT 5"),
            ("marcador_walkover", "INTEGER NOT NULL DEFAULT 3"),
        ],
        "lugar": [("capacidad", "INTEGER"), ("superficie", "VARCHAR(80)")],
        "equipo": [("activo", "BOOLEAN NOT NULL DEFAULT 1")],
        "alumno": [("fecha_retiro", "DATE")],
        "cierre_caja": [("reabierto_en", "DATETIME"), ("motivo_reapertura", "VARCHAR(255)")],
        "partido": [("id_lugar", "INTEGER REFERENCES lugar(id_lugar) ON DELETE SET NULL")],
        "evento_agenda": [("id_lugar", "INTEGER REFERENCES lugar(id_lugar) ON DELETE SET NULL")],
        "entrenamiento": [
            ("id_lugar", "INTEGER REFERENCES lugar(id_lugar) ON DELETE SET NULL"),
            ("fecha_inicio", "DATE"), ("fecha_fin", "DATE"),
        ],
        "campeonato": [
            ("id_lugar", "INTEGER REFERENCES lugar(id_lugar) ON DELETE SET NULL"),
            ("motivo_reapertura", "VARCHAR(255)"),
        ],
    }
    for tabla, definiciones in columnas_por_tabla.items():
        existentes = _columnas(tabla)
        for nombre, definicion in definiciones:
            if nombre not in existentes:
                db.session.execute(text(
                    f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}"
                ))
    for tabla, columna_texto in (
        ("partido", "cancha"), ("evento_agenda", "lugar"),
        ("entrenamiento", "lugar"), ("campeonato", "lugar"),
    ):
        db.session.execute(text(
            f"UPDATE {tabla} SET id_lugar=(SELECT l.id_lugar FROM lugar l "
            f"WHERE lower(trim(l.nombre))=lower(trim({tabla}.{columna_texto})) LIMIT 1) "
            f"WHERE id_lugar IS NULL AND {columna_texto} IS NOT NULL"
        ))
    db.session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_qr_operacion_activa "
        "ON pago(numero_operacion) WHERE eliminado_en IS NULL AND modo_pago='QR' "
        "AND numero_operacion IS NOT NULL AND trim(numero_operacion)<>''"
    ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_agenda_fecha_tipo ON evento_agenda(fecha, tipo)"
    ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_entrenamiento_vigencia "
        "ON entrenamiento(activo, fecha_inicio, fecha_fin)"
    ))
    db.session.commit()


def _migracion_11_google_maps_lugares():
    if "google_maps_url" not in _columnas("lugar"):
        db.session.execute(text(
            "ALTER TABLE lugar ADD COLUMN google_maps_url VARCHAR(600)"
        ))
    db.session.commit()


def _migracion_12_acceso_con_contrasena():
    if "contrasena_hash" not in _columnas("configuracion"):
        db.session.execute(text(
            "ALTER TABLE configuracion ADD COLUMN contrasena_hash VARCHAR(255)"
        ))
    db.session.commit()


def _migracion_13_gestion_ficha():
    if "gestion_ficha" not in _columnas("configuracion"):
        gestion = datetime.now().year
        db.session.execute(text(
            f"ALTER TABLE configuracion ADD COLUMN gestion_ficha "
            f"INTEGER NOT NULL DEFAULT {gestion}"
        ))
    db.session.commit()


def _migracion_14_marca_contabilidad_inventario():
    nuevas = [
        ("eslogan", "VARCHAR(180)"),
        ("logo", "VARCHAR(255)"),
        ("color_primario", "VARCHAR(7) NOT NULL DEFAULT '#2563eb'"),
        ("color_secundario", "VARCHAR(7) NOT NULL DEFAULT '#0f172a'"),
        ("color_acento", "VARCHAR(7) NOT NULL DEFAULT '#16a34a'"),
    ]
    existentes = _columnas("configuracion")
    for nombre, definicion in nuevas:
        if nombre not in existentes:
            db.session.execute(text(
                f"ALTER TABLE configuracion ADD COLUMN {nombre} {definicion}"
            ))
    db.session.execute(text(
        "UPDATE configuracion SET nombre_academia='Mi Academia Deportiva' "
        "WHERE lower(nombre_academia) LIKE '%atlas%'"
    ))
    # Los pagos válidos históricos se incorporan una sola vez a contabilidad.
    db.session.execute(text(
        "INSERT OR IGNORE INTO movimiento_contable "
        "(tipo,categoria,concepto,monto,fecha,modo_pago,numero_operacion,"
        "origen_tipo,origen_id,creado_en) "
        "SELECT 'Ingreso','Mensualidades','Mensualidad ' || p.mes_pagado,"
        "p.monto,p.fecha_pago,p.modo_pago,p.numero_operacion,'Pago',p.id_pago,"
        "COALESCE(p.creado_en,CURRENT_TIMESTAMP) FROM pago p "
        "WHERE p.eliminado_en IS NULL AND p.es_beca=0 AND p.monto>0"
    ))
    db.session.commit()


def _migracion_15_integridad_y_rendimiento():
    indices = [
        "CREATE INDEX IF NOT EXISTS ix_alumno_categoria ON alumno(id_categoria)",
        "CREATE INDEX IF NOT EXISTS ix_pago_alumno_fecha ON pago(id_alumno,fecha_pago)",
        "CREATE INDEX IF NOT EXISTS ix_historial_alumno ON historial_alumno(id_alumno)",
        "CREATE INDEX IF NOT EXISTS ix_movimiento_fecha_tipo ON movimiento_contable(fecha,tipo)",
        "CREATE INDEX IF NOT EXISTS ix_movimiento_proveedor ON movimiento_contable(id_proveedor)",
        "CREATE INDEX IF NOT EXISTS ix_variante_producto ON producto_variante(id_producto)",
        "CREATE INDEX IF NOT EXISTS ix_inventario_variante ON movimiento_inventario(id_variante,creado_en)",
        "CREATE INDEX IF NOT EXISTS ix_venta_alumno_fecha ON venta(id_alumno,fecha)",
        "CREATE INDEX IF NOT EXISTS ix_detalle_venta ON detalle_venta(id_venta)",
        "CREATE INDEX IF NOT EXISTS ix_partido_campeonato_fecha ON partido(id_campeonato,fecha)",
        "CREATE INDEX IF NOT EXISTS ix_partido_categoria_fecha ON partido(id_categoria,fecha)",
        "CREATE INDEX IF NOT EXISTS ix_evento_fecha ON evento_agenda(fecha)",
        "CREATE INDEX IF NOT EXISTS ix_evento_partido ON evento_agenda(id_partido)",
        "CREATE INDEX IF NOT EXISTS ix_posicion_campeonato_categoria ON posicion(id_campeonato,id_categoria)",
    ]
    for sentencia in indices:
        db.session.execute(text(sentencia))

    validaciones = {
        "movimiento_contable": (
            "NEW.monto < 0 OR NEW.tipo NOT IN ('Ingreso','Egreso') OR "
            "NEW.modo_pago NOT IN ('Efectivo','QR','Transferencia','Otro') OR "
            "((NEW.origen_tipo IS NULL) <> (NEW.origen_id IS NULL))"
        ),
        "producto_variante": (
            "NEW.stock < 0 OR NEW.stock_minimo < 0 OR NEW.precio_compra < 0 OR NEW.precio_venta < 0"
        ),
        "movimiento_inventario": (
            "NEW.cantidad = 0 OR NEW.stock_anterior < 0 OR NEW.stock_nuevo < 0 OR "
            "NEW.stock_nuevo <> NEW.stock_anterior + NEW.cantidad"
        ),
        "venta": (
            "NEW.subtotal < 0 OR NEW.descuento < 0 OR NEW.total < 0 OR "
            "NEW.descuento > NEW.subtotal OR abs(NEW.total-(NEW.subtotal-NEW.descuento)) >= 0.01 OR "
            "(NEW.id_alumno IS NULL AND length(trim(COALESCE(NEW.cliente_externo,''))) = 0) OR "
            "NEW.modo_pago NOT IN ('Efectivo','QR','Transferencia','Otro')"
        ),
        "detalle_venta": (
            "NEW.cantidad <= 0 OR NEW.precio_unitario < 0 OR NEW.subtotal < 0 OR "
            "abs(NEW.subtotal-(NEW.precio_unitario*NEW.cantidad)) >= 0.01"
        ),
    }
    for tabla, condicion in validaciones.items():
        for operacion in ("INSERT", "UPDATE"):
            nombre = f"trg_{tabla}_{operacion.lower()}_integridad"
            db.session.execute(text(
                f"CREATE TRIGGER IF NOT EXISTS {nombre} BEFORE {operacion} ON {tabla} "
                f"WHEN {condicion} BEGIN SELECT RAISE(ABORT, 'Datos inválidos en {tabla}'); END"
            ))
    db.session.commit()


def _migracion_16_indices_foraneos_completos():
    indices = [
        "CREATE INDEX IF NOT EXISTS ix_anulacion_reemplazo ON anulacion_pago(id_pago_reemplazo)",
        "CREATE INDEX IF NOT EXISTS ix_campeonato_lugar ON campeonato(id_lugar)",
        "CREATE INDEX IF NOT EXISTS ix_detalle_variante ON detalle_venta(id_variante)",
        "CREATE INDEX IF NOT EXISTS ix_entrenamiento_equipo ON entrenamiento(id_equipo)",
        "CREATE INDEX IF NOT EXISTS ix_entrenamiento_categoria ON entrenamiento(id_categoria)",
        "CREATE INDEX IF NOT EXISTS ix_entrenamiento_lugar ON entrenamiento(id_lugar)",
        "CREATE INDEX IF NOT EXISTS ix_evento_equipo ON evento_agenda(id_equipo)",
        "CREATE INDEX IF NOT EXISTS ix_evento_categoria ON evento_agenda(id_categoria)",
        "CREATE INDEX IF NOT EXISTS ix_evento_lugar ON evento_agenda(id_lugar)",
        "CREATE INDEX IF NOT EXISTS ix_partido_equipo ON partido(id_equipo)",
        "CREATE INDEX IF NOT EXISTS ix_partido_lugar ON partido(id_lugar)",
        "CREATE INDEX IF NOT EXISTS ix_podio_tercero ON podio_campeonato(id_tercero)",
        "CREATE INDEX IF NOT EXISTS ix_podio_subcampeon ON podio_campeonato(id_subcampeon)",
        "CREATE INDEX IF NOT EXISTS ix_podio_campeon ON podio_campeonato(id_campeon)",
    ]
    for sentencia in indices:
        db.session.execute(text(sentencia))
    db.session.commit()


def _migracion_17_pagos_programados():
    sentencias = [
        "CREATE INDEX IF NOT EXISTS ix_programado_proveedor ON pago_programado(id_proveedor)",
        "CREATE INDEX IF NOT EXISTS ix_programado_proxima ON pago_programado(activo,proxima_fecha)",
        "CREATE INDEX IF NOT EXISTS ix_cuota_estado_fecha ON cuota_programada(estado,fecha_vencimiento)",
        "CREATE INDEX IF NOT EXISTS ix_cuota_programado ON cuota_programada(id_programado,fecha_vencimiento)",
    ]
    for sentencia in sentencias:
        db.session.execute(text(sentencia))
    db.session.commit()


def _migracion_18_categorias_contables():
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS categoria_contable (
        id_categoria_contable INTEGER NOT NULL PRIMARY KEY,
        nombre VARCHAR(80) NOT NULL UNIQUE,
        tipo VARCHAR(10) NOT NULL DEFAULT 'Ambos', activo BOOLEAN NOT NULL DEFAULT 1,
        creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT ck_categoria_contable_tipo CHECK (tipo IN ('Ingreso','Egreso','Ambos'))
    )"""))
    db.session.execute(text("""INSERT OR IGNORE INTO categoria_contable(nombre,tipo,activo,creado_en)
        SELECT categoria, CASE WHEN MIN(tipo)=MAX(tipo) THEN MIN(tipo) ELSE 'Ambos' END, 1, CURRENT_TIMESTAMP
        FROM movimiento_contable WHERE length(trim(categoria)) > 0 GROUP BY categoria"""))
    db.session.execute(text("""INSERT OR IGNORE INTO categoria_contable(nombre,tipo,activo,creado_en)
        SELECT categoria,'Egreso',1,CURRENT_TIMESTAMP FROM pago_programado WHERE length(trim(categoria)) > 0"""))
    db.session.commit()


def _migracion_19_usuarios_roles_auditoria():
    columnas = _columnas("auditoria")
    if "id_usuario" not in columnas:
        db.session.execute(text("ALTER TABLE auditoria ADD COLUMN id_usuario INTEGER REFERENCES usuario(id_usuario)"))
    if "valor_anterior" not in columnas:
        db.session.execute(text("ALTER TABLE auditoria ADD COLUMN valor_anterior TEXT"))
    if "valor_nuevo" not in columnas:
        db.session.execute(text("ALTER TABLE auditoria ADD COLUMN valor_nuevo TEXT"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_auditoria_usuario_fecha ON auditoria(id_usuario,creado_en)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_usuario_rol ON usuario(id_rol)"))
    db.session.commit()


def _migracion_20_obligaciones_y_abonos():
    """Separa la deuda de sus pagos conservando intactos los comprobantes."""
    db.session.execute(text("DROP INDEX IF EXISTS uq_pago_activo_mes"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_pago_alumno_mes ON pago(id_alumno,mes_pagado)"))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS obligacion (
        id_obligacion INTEGER NOT NULL PRIMARY KEY,
        id_alumno INTEGER NOT NULL REFERENCES alumno(id_alumno) ON DELETE RESTRICT,
        concepto VARCHAR(40) NOT NULL DEFAULT 'Mensualidad', periodo VARCHAR(7) NOT NULL,
        monto_original NUMERIC(10,2) NOT NULL, descuento NUMERIC(10,2) NOT NULL DEFAULT 0,
        recargo NUMERIC(10,2) NOT NULL DEFAULT 0, cubierto_beca BOOLEAN NOT NULL DEFAULT 0,
        fecha_vencimiento DATE NOT NULL, creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_obligacion_alumno_concepto_periodo UNIQUE(id_alumno,concepto,periodo),
        CONSTRAINT ck_obligacion_importes CHECK(monto_original>=0 AND descuento>=0 AND recargo>=0)
    )"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS aplicacion_pago (
        id_aplicacion INTEGER NOT NULL PRIMARY KEY,
        id_obligacion INTEGER NOT NULL REFERENCES obligacion(id_obligacion) ON DELETE RESTRICT,
        id_pago INTEGER NOT NULL UNIQUE REFERENCES pago(id_pago) ON DELETE RESTRICT,
        monto NUMERIC(10,2) NOT NULL, creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS tarifa (
        id_tarifa INTEGER NOT NULL PRIMARY KEY, concepto VARCHAR(40) NOT NULL DEFAULT 'Mensualidad',
        monto NUMERIC(10,2) NOT NULL, fecha_inicio DATE NOT NULL, fecha_fin DATE,
        id_categoria INTEGER REFERENCES categoria(id_categoria), activo BOOLEAN NOT NULL DEFAULT 1,
        creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS beca_historial (
        id_beca INTEGER NOT NULL PRIMARY KEY,
        id_alumno INTEGER NOT NULL REFERENCES alumno(id_alumno) ON DELETE RESTRICT,
        porcentaje NUMERIC(5,2) NOT NULL, fecha_inicio DATE NOT NULL, fecha_fin DATE,
        motivo VARCHAR(255), autorizado_por VARCHAR(120),
        creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )"""))
    db.session.execute(text("""INSERT OR IGNORE INTO obligacion
        (id_alumno,concepto,periodo,monto_original,descuento,recargo,cubierto_beca,fecha_vencimiento,creado_en)
        SELECT id_alumno,'Mensualidad',mes_pagado,monto,0,0,es_beca,fecha_vencimiento,creado_en FROM pago"""))
    db.session.execute(text("""INSERT OR IGNORE INTO aplicacion_pago(id_obligacion,id_pago,monto,creado_en)
        SELECT o.id_obligacion,p.id_pago,p.monto,p.creado_en FROM pago p JOIN obligacion o
        ON o.id_alumno=p.id_alumno AND o.concepto='Mensualidad' AND o.periodo=p.mes_pagado"""))
    db.session.execute(text("""INSERT INTO tarifa(concepto,monto,fecha_inicio,activo,creado_en)
        SELECT 'Mensualidad',monto_mensualidad,date('now'),1,CURRENT_TIMESTAMP FROM configuracion
        WHERE NOT EXISTS (SELECT 1 FROM tarifa WHERE concepto='Mensualidad')"""))
    db.session.execute(text("""INSERT INTO beca_historial(id_alumno,porcentaje,fecha_inicio,fecha_fin,motivo,creado_en)
        SELECT id_alumno,CASE beca WHEN 'Completa' THEN 100 WHEN 'Media' THEN 50 ELSE 0 END,
        COALESCE(date(creado_en),date('now')),beca_fecha_fin,'Migración del estado vigente',CURRENT_TIMESTAMP
        FROM alumno WHERE beca!='Ninguna' AND NOT EXISTS
        (SELECT 1 FROM beca_historial b WHERE b.id_alumno=alumno.id_alumno)"""))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_obligacion_alumno_periodo ON obligacion(id_alumno,periodo)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_aplicacion_obligacion ON aplicacion_pago(id_obligacion)"))
    db.session.commit()


def _migracion_21_sesiones_caja():
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS sesion_caja (
        id_sesion INTEGER NOT NULL PRIMARY KEY,
        id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
        abierta_en DATETIME NOT NULL, saldo_inicial NUMERIC(12,2) NOT NULL DEFAULT 0,
        cerrada_en DATETIME, efectivo_esperado NUMERIC(12,2), efectivo_contado NUMERIC(12,2),
        diferencia NUMERIC(12,2), estado VARCHAR(12) NOT NULL DEFAULT 'Abierta',
        observacion VARCHAR(255), motivo_reapertura VARCHAR(255),
        id_cierre_legacy INTEGER UNIQUE REFERENCES cierre_caja(id_cierre) ON DELETE SET NULL,
        CONSTRAINT ck_sesion_caja_estado CHECK(estado IN ('Abierta','Cerrada','Reabierta')),
        CONSTRAINT ck_sesion_caja_saldo_inicial CHECK(saldo_inicial>=0)
    )"""))
    if "id_sesion_caja" not in _columnas("movimiento_contable"):
        db.session.execute(text("ALTER TABLE movimiento_contable ADD COLUMN id_sesion_caja INTEGER REFERENCES sesion_caja(id_sesion) ON DELETE SET NULL"))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS movimiento_caja (
        id_movimiento_caja INTEGER NOT NULL PRIMARY KEY,
        id_sesion INTEGER NOT NULL REFERENCES sesion_caja(id_sesion) ON DELETE RESTRICT,
        id_movimiento_contable INTEGER NOT NULL UNIQUE REFERENCES movimiento_contable(id_movimiento) ON DELETE RESTRICT,
        tipo VARCHAR(10) NOT NULL, monto NUMERIC(12,2) NOT NULL,
        modo_pago VARCHAR(20) NOT NULL, creado_en DATETIME NOT NULL
    )"""))
    # Cada cierre anterior se conserva como una sesión histórica del administrador.
    db.session.execute(text("""INSERT OR IGNORE INTO sesion_caja
        (id_usuario,abierta_en,saldo_inicial,cerrada_en,efectivo_esperado,efectivo_contado,diferencia,estado,observacion,id_cierre_legacy)
        SELECT (SELECT id_usuario FROM usuario WHERE nombre_usuario='admin' LIMIT 1),
        datetime(c.fecha || ' 00:00:00'),0,c.cerrado_en,c.efectivo_sistema,c.efectivo_contado,c.diferencia,
        CASE WHEN c.reabierto_en IS NULL THEN 'Cerrada' ELSE 'Reabierta' END,c.observacion,c.id_cierre
        FROM cierre_caja c WHERE EXISTS(SELECT 1 FROM usuario WHERE nombre_usuario='admin')"""))
    db.session.execute(text("""UPDATE movimiento_contable SET id_sesion_caja=(
        SELECT s.id_sesion FROM sesion_caja s JOIN cierre_caja c ON c.id_cierre=s.id_cierre_legacy
        WHERE c.fecha=movimiento_contable.fecha LIMIT 1)
        WHERE id_sesion_caja IS NULL AND EXISTS(SELECT 1 FROM sesion_caja s JOIN cierre_caja c
        ON c.id_cierre=s.id_cierre_legacy WHERE c.fecha=movimiento_contable.fecha)"""))
    db.session.execute(text("""INSERT OR IGNORE INTO movimiento_caja
        (id_sesion,id_movimiento_contable,tipo,monto,modo_pago,creado_en)
        SELECT id_sesion_caja,id_movimiento,tipo,monto,modo_pago,creado_en FROM movimiento_contable
        WHERE id_sesion_caja IS NOT NULL"""))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_sesion_caja_usuario_estado ON sesion_caja(id_usuario,estado)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_movimiento_caja_sesion ON movimiento_caja(id_sesion,creado_en)"))
    db.session.commit()


def _migracion_22_compras_e_integridad_cruzada():
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS compra (
        id_compra INTEGER NOT NULL PRIMARY KEY,
        id_proveedor INTEGER NOT NULL REFERENCES proveedor(id_proveedor) ON DELETE RESTRICT,
        fecha DATE NOT NULL, numero_factura VARCHAR(80), modo_pago VARCHAR(20) NOT NULL,
        total NUMERIC(12,2) NOT NULL, observacion VARCHAR(255), anulado_en DATETIME,
        motivo_anulacion VARCHAR(255), creado_en DATETIME NOT NULL,
        CONSTRAINT ck_compra_total CHECK(total>=0),
        CONSTRAINT ck_compra_modo CHECK(modo_pago IN ('Efectivo','QR','Transferencia','Otro'))
    )"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS detalle_compra (
        id_detalle_compra INTEGER NOT NULL PRIMARY KEY,
        id_compra INTEGER NOT NULL REFERENCES compra(id_compra) ON DELETE RESTRICT,
        id_variante INTEGER NOT NULL REFERENCES producto_variante(id_variante) ON DELETE RESTRICT,
        cantidad INTEGER NOT NULL, costo_unitario NUMERIC(12,2) NOT NULL,
        subtotal NUMERIC(12,2) NOT NULL,
        CONSTRAINT ck_detalle_compra_cantidad CHECK(cantidad>0),
        CONSTRAINT ck_detalle_compra_montos CHECK(costo_unitario>=0 AND subtotal>=0),
        CONSTRAINT ck_detalle_compra_subtotal CHECK(abs(subtotal-(costo_unitario*cantidad))<0.01)
    )"""))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_compra_proveedor_fecha ON compra(id_proveedor,fecha)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_detalle_compra_variante ON detalle_compra(id_variante)"))
    db.session.commit()


def _migracion_23_fuente_deportiva_y_conflictos():
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS conflicto_autorizado (
        id_conflicto INTEGER NOT NULL PRIMARY KEY, tipo_entidad VARCHAR(30) NOT NULL,
        id_entidad INTEGER NOT NULL, tipo_conflicto VARCHAR(40) NOT NULL,
        referencia VARCHAR(120) NOT NULL, motivo VARCHAR(255) NOT NULL,
        id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
        creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )"""))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_conflicto_entidad ON conflicto_autorizado(tipo_entidad,id_entidad)"))
    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_agenda_partido_unico ON evento_agenda(id_partido) WHERE id_partido IS NOT NULL"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_partido_programacion ON partido(fecha,hora,id_lugar,id_equipo)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_evento_programacion ON evento_agenda(fecha,hora,id_lugar,id_equipo)"))
    db.session.commit()


def _migracion_24_inscripciones_e_historiales():
    """Conserva el estado vigente y lo convierte en historia por gestión."""
    columnas_beca = _columnas("beca_historial")
    if "estado" not in columnas_beca:
        db.session.execute(text("ALTER TABLE beca_historial ADD COLUMN estado VARCHAR(12) NOT NULL DEFAULT 'Activa'"))
    if "id_usuario" not in columnas_beca:
        db.session.execute(text("ALTER TABLE beca_historial ADD COLUMN id_usuario INTEGER REFERENCES usuario(id_usuario) ON DELETE SET NULL"))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS inscripcion_gestion (
        id_inscripcion INTEGER NOT NULL PRIMARY KEY,
        id_alumno INTEGER NOT NULL REFERENCES alumno(id_alumno) ON DELETE RESTRICT,
        gestion INTEGER NOT NULL, fecha_inscripcion DATE NOT NULL, fecha_fin DATE,
        estado VARCHAR(15) NOT NULL DEFAULT 'Activa',
        id_categoria INTEGER REFERENCES categoria(id_categoria) ON DELETE SET NULL,
        id_equipo_principal INTEGER REFERENCES equipo(id_equipo) ON DELETE SET NULL,
        id_tarifa INTEGER REFERENCES tarifa(id_tarifa) ON DELETE SET NULL,
        monto_tarifa NUMERIC(10,2), porcentaje_beca NUMERIC(5,2) NOT NULL DEFAULT 0,
        observacion VARCHAR(255), creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_inscripcion_alumno_gestion UNIQUE(id_alumno,gestion),
        CONSTRAINT ck_inscripcion_beca CHECK(porcentaje_beca>=0 AND porcentaje_beca<=100)
    )"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS historial_categoria_alumno (
        id_historial_categoria INTEGER NOT NULL PRIMARY KEY,
        id_alumno INTEGER NOT NULL REFERENCES alumno(id_alumno) ON DELETE RESTRICT,
        id_categoria INTEGER NOT NULL REFERENCES categoria(id_categoria) ON DELETE RESTRICT,
        fecha_inicio DATE NOT NULL, fecha_fin DATE, tipo_asignacion VARCHAR(10) NOT NULL,
        motivo VARCHAR(255), bloqueada_hasta DATE,
        id_usuario INTEGER REFERENCES usuario(id_usuario) ON DELETE SET NULL,
        migrado_sin_fecha BOOLEAN NOT NULL DEFAULT 0
    )"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS historial_equipo_alumno (
        id_historial_equipo INTEGER NOT NULL PRIMARY KEY,
        id_alumno INTEGER NOT NULL REFERENCES alumno(id_alumno) ON DELETE RESTRICT,
        id_equipo INTEGER NOT NULL REFERENCES equipo(id_equipo) ON DELETE RESTRICT,
        gestion INTEGER NOT NULL, fecha_inicio DATE NOT NULL, fecha_fin DATE,
        estado VARCHAR(12) NOT NULL DEFAULT 'Activa', motivo_salida VARCHAR(255),
        principal BOOLEAN NOT NULL DEFAULT 0,
        id_usuario INTEGER REFERENCES usuario(id_usuario) ON DELETE SET NULL,
        migrado_sin_fecha BOOLEAN NOT NULL DEFAULT 0
    )"""))
    tiene_categoria_alumno = "id_categoria" in _columnas("alumno")
    categoria_alumno = "a.id_categoria" if tiene_categoria_alumno else "NULL"
    # SQLite no admite referenciar la consulta exterior desde ORDER BY de esta
    # subconsulta; la categoría sí queda guardada y la tarifa específica se
    # resolverá al crear cada obligación.
    prioridad_tarifa = "(t.id_categoria IS NULL)"
    db.session.execute(text(f"""INSERT OR IGNORE INTO inscripcion_gestion
        (id_alumno,gestion,fecha_inscripcion,estado,id_categoria,id_equipo_principal,
         id_tarifa,monto_tarifa,porcentaje_beca,observacion,creado_en)
        SELECT a.id_alumno,COALESCE(c.gestion_ficha,CAST(strftime('%Y','now') AS INTEGER)),
        COALESCE(date(a.creado_en),date('now')),
        CASE WHEN a.estado='Activo' THEN 'Activa' ELSE 'Retirada' END,{categoria_alumno},
        (SELECT MIN(ae.id_equipo) FROM alumno_equipo ae WHERE ae.id_alumno=a.id_alumno),
        (SELECT t.id_tarifa FROM tarifa t WHERE t.concepto='Mensualidad' AND t.activo=1
         ORDER BY {prioridad_tarifa} DESC,t.fecha_inicio DESC LIMIT 1),
        NULL,CASE a.beca WHEN 'Completa' THEN 100 WHEN 'Media' THEN 50 ELSE 0 END,
        'Migrado desde el estado vigente; fecha histórica aproximada',CURRENT_TIMESTAMP
        FROM alumno a CROSS JOIN configuracion c"""))
    if tiene_categoria_alumno:
        db.session.execute(text("""INSERT INTO historial_categoria_alumno
        (id_alumno,id_categoria,fecha_inicio,tipo_asignacion,motivo,migrado_sin_fecha)
        SELECT a.id_alumno,a.id_categoria,COALESCE(date(a.creado_en),date('now')),
        CASE WHEN a.categoria_manual=1 THEN 'Manual' ELSE 'Automática' END,
        'Migrado desde la categoría vigente',1 FROM alumno a WHERE a.id_categoria IS NOT NULL
        AND NOT EXISTS(SELECT 1 FROM historial_categoria_alumno h WHERE h.id_alumno=a.id_alumno)"""))
    db.session.execute(text("""INSERT INTO historial_equipo_alumno
        (id_alumno,id_equipo,gestion,fecha_inicio,estado,principal,migrado_sin_fecha)
        SELECT ae.id_alumno,ae.id_equipo,COALESCE(c.gestion_ficha,CAST(strftime('%Y','now') AS INTEGER)),
        COALESCE(date(a.creado_en),date('now')),'Activa',
        CASE WHEN ae.id_equipo=(SELECT MIN(x.id_equipo) FROM alumno_equipo x WHERE x.id_alumno=ae.id_alumno) THEN 1 ELSE 0 END,1
        FROM alumno_equipo ae JOIN alumno a ON a.id_alumno=ae.id_alumno CROSS JOIN configuracion c
        WHERE NOT EXISTS(SELECT 1 FROM historial_equipo_alumno h
        WHERE h.id_alumno=ae.id_alumno AND h.id_equipo=ae.id_equipo AND h.fecha_fin IS NULL)"""))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_inscripcion_gestion_estado ON inscripcion_gestion(gestion,estado)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_hist_categoria_alumno_fecha ON historial_categoria_alumno(id_alumno,fecha_inicio)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_hist_equipo_alumno_fecha ON historial_equipo_alumno(id_alumno,fecha_inicio)"))
    db.session.commit()


def _migracion_25_catalogos_historicos():
    """Vincula categorías por ID sin modificar el texto histórico mostrado."""
    for tabla in ("movimiento_contable", "pago_programado"):
        if "id_categoria_contable" not in _columnas(tabla):
            db.session.execute(text(
                f"ALTER TABLE {tabla} ADD COLUMN id_categoria_contable INTEGER "
                "REFERENCES categoria_contable(id_categoria_contable) ON DELETE RESTRICT"
            ))
        db.session.execute(text(f"""UPDATE {tabla} SET id_categoria_contable=(
            SELECT c.id_categoria_contable FROM categoria_contable c
            WHERE lower(trim(c.nombre))=lower(trim({tabla}.categoria)) LIMIT 1)
            WHERE id_categoria_contable IS NULL"""))
        db.session.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{tabla}_categoria_id ON {tabla}(id_categoria_contable)"))
    columnas = _columnas("proveedor")
    for nombre, definicion in (
        ("tipo_persona", "VARCHAR(10) NOT NULL DEFAULT 'Persona'"),
        ("documento", "VARCHAR(40)"), ("correo", "VARCHAR(120)"),
        ("contacto", "VARCHAR(120)"),
    ):
        if nombre not in columnas:
            db.session.execute(text(f"ALTER TABLE proveedor ADD COLUMN {nombre} {definicion}"))
    db.session.commit()


def _migracion_26_personal_y_asistencia():
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS personal_deportivo (
        id_personal INTEGER NOT NULL PRIMARY KEY, nombre VARCHAR(150) NOT NULL,
        documento VARCHAR(40) UNIQUE, telefono VARCHAR(40), correo VARCHAR(120),
        especialidad VARCHAR(120), tipo VARCHAR(20) NOT NULL DEFAULT 'Entrenador',
        fecha_ingreso DATE NOT NULL, fecha_salida DATE, activo BOOLEAN NOT NULL DEFAULT 1,
        observacion VARCHAR(255)
    )"""))
    if "id_entrenador" not in _columnas("entrenamiento"):
        db.session.execute(text("ALTER TABLE entrenamiento ADD COLUMN id_entrenador INTEGER REFERENCES personal_deportivo(id_personal) ON DELETE SET NULL"))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS sesion_entrenamiento (
        id_sesion_entrenamiento INTEGER NOT NULL PRIMARY KEY,
        id_entrenamiento INTEGER NOT NULL REFERENCES entrenamiento(id_entrenamiento) ON DELETE RESTRICT,
        fecha DATE NOT NULL, estado VARCHAR(12) NOT NULL DEFAULT 'Programada',
        observacion VARCHAR(255), creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_sesion_entrenamiento_fecha UNIQUE(id_entrenamiento,fecha)
    )"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS asistencia_entrenamiento (
        id_asistencia INTEGER NOT NULL PRIMARY KEY,
        id_sesion_entrenamiento INTEGER NOT NULL REFERENCES sesion_entrenamiento(id_sesion_entrenamiento) ON DELETE CASCADE,
        id_alumno INTEGER NOT NULL REFERENCES alumno(id_alumno) ON DELETE RESTRICT,
        estado VARCHAR(12) NOT NULL DEFAULT 'Presente', justificacion VARCHAR(255),
        registrado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_asistencia_sesion_alumno UNIQUE(id_sesion_entrenamiento,id_alumno)
    )"""))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_asistencia_alumno ON asistencia_entrenamiento(id_alumno)"))
    db.session.commit()


def _migracion_27_tutores_conteos_devoluciones():
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS tutor (
        id_tutor INTEGER NOT NULL PRIMARY KEY, nombre VARCHAR(150) NOT NULL,
        documento VARCHAR(40), telefono VARCHAR(40), correo VARCHAR(120),
        direccion VARCHAR(255), activo BOOLEAN NOT NULL DEFAULT 1)"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS alumno_tutor (
        id_alumno_tutor INTEGER NOT NULL PRIMARY KEY,
        id_alumno INTEGER NOT NULL REFERENCES alumno(id_alumno) ON DELETE CASCADE,
        id_tutor INTEGER NOT NULL REFERENCES tutor(id_tutor) ON DELETE RESTRICT,
        parentesco VARCHAR(30), principal BOOLEAN NOT NULL DEFAULT 0,
        autorizado_recoger BOOLEAN NOT NULL DEFAULT 1,
        CONSTRAINT uq_alumno_tutor UNIQUE(id_alumno,id_tutor))"""))
    # Los nombres heredados se migran sin fusionar automáticamente homónimos.
    db.session.execute(text("""INSERT INTO tutor(nombre,activo)
        SELECT DISTINCT trim(tutor),1 FROM alumno WHERE tutor IS NOT NULL AND trim(tutor)<>''
        AND NOT EXISTS(SELECT 1 FROM tutor t WHERE lower(trim(t.nombre))=lower(trim(alumno.tutor)))"""))
    db.session.execute(text("""INSERT OR IGNORE INTO alumno_tutor(id_alumno,id_tutor,principal,autorizado_recoger)
        SELECT a.id_alumno,t.id_tutor,1,1 FROM alumno a JOIN tutor t
        ON lower(trim(t.nombre))=lower(trim(a.tutor)) WHERE a.tutor IS NOT NULL AND trim(a.tutor)<>''"""))
    db.session.execute(text("""INSERT INTO tutor(nombre,activo)
        SELECT DISTINCT trim(tutor2),1 FROM alumno WHERE tutor2 IS NOT NULL AND trim(tutor2)<>''
        AND NOT EXISTS(SELECT 1 FROM tutor t WHERE lower(trim(t.nombre))=lower(trim(alumno.tutor2)))"""))
    db.session.execute(text("""INSERT OR IGNORE INTO alumno_tutor(id_alumno,id_tutor,principal,autorizado_recoger)
        SELECT a.id_alumno,t.id_tutor,0,1 FROM alumno a JOIN tutor t
        ON lower(trim(t.nombre))=lower(trim(a.tutor2)) WHERE a.tutor2 IS NOT NULL AND trim(a.tutor2)<>''"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS conteo_inventario (
        id_conteo INTEGER NOT NULL PRIMARY KEY, fecha DATE NOT NULL,
        estado VARCHAR(12) NOT NULL DEFAULT 'Pendiente', observacion VARCHAR(255),
        creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS detalle_conteo_inventario (
        id_detalle_conteo INTEGER NOT NULL PRIMARY KEY,
        id_conteo INTEGER NOT NULL REFERENCES conteo_inventario(id_conteo) ON DELETE CASCADE,
        id_variante INTEGER NOT NULL REFERENCES producto_variante(id_variante) ON DELETE RESTRICT,
        stock_sistema INTEGER NOT NULL, stock_contado INTEGER NOT NULL,
        CONSTRAINT uq_conteo_variante UNIQUE(id_conteo,id_variante))"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS devolucion_venta (
        id_devolucion INTEGER NOT NULL PRIMARY KEY,
        id_venta INTEGER NOT NULL REFERENCES venta(id_venta) ON DELETE RESTRICT,
        fecha DATE NOT NULL, tipo VARCHAR(12) NOT NULL DEFAULT 'Devolución',
        total_credito NUMERIC(12,2) NOT NULL DEFAULT 0, motivo VARCHAR(255) NOT NULL,
        creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"""))
    db.session.execute(text("""CREATE TABLE IF NOT EXISTS detalle_devolucion_venta (
        id_detalle_devolucion INTEGER NOT NULL PRIMARY KEY,
        id_devolucion INTEGER NOT NULL REFERENCES devolucion_venta(id_devolucion) ON DELETE CASCADE,
        id_detalle_venta INTEGER NOT NULL REFERENCES detalle_venta(id_detalle) ON DELETE RESTRICT,
        cantidad INTEGER NOT NULL, subtotal NUMERIC(12,2) NOT NULL)"""))
    db.session.commit()


def _migracion_28_reparar_relaciones_tutores():
    db.session.execute(text("""INSERT OR IGNORE INTO alumno_tutor
        (id_alumno,id_tutor,principal,autorizado_recoger)
        SELECT a.id_alumno,t.id_tutor,1,1 FROM alumno a JOIN tutor t
        ON lower(trim(t.nombre))=lower(trim(a.tutor))
        WHERE a.tutor IS NOT NULL AND trim(a.tutor)<>''"""))
    db.session.execute(text("""INSERT OR IGNORE INTO alumno_tutor
        (id_alumno,id_tutor,principal,autorizado_recoger)
        SELECT a.id_alumno,t.id_tutor,0,1 FROM alumno a JOIN tutor t
        ON lower(trim(t.nombre))=lower(trim(a.tutor2))
        WHERE a.tutor2 IS NOT NULL AND trim(a.tutor2)<>''"""))
    db.session.commit()


def _migracion_29_indices_y_permisos_operativos():
    indices = [
        ("ix_beca_historial_alumno", "beca_historial", "id_alumno"),
        ("ix_beca_historial_usuario", "beca_historial", "id_usuario"),
        ("ix_conflicto_autorizado_usuario", "conflicto_autorizado", "id_usuario"),
        ("ix_detalle_compra_compra", "detalle_compra", "id_compra"),
        ("ix_detalle_devolucion_detalle", "detalle_devolucion_venta", "id_detalle_venta"),
        ("ix_detalle_devolucion_devolucion", "detalle_devolucion_venta", "id_devolucion"),
        ("ix_devolucion_venta", "devolucion_venta", "id_venta"),
        ("ix_entrenamiento_entrenador", "entrenamiento", "id_entrenador"),
        ("ix_hist_categoria_usuario", "historial_categoria_alumno", "id_usuario"),
        ("ix_hist_categoria_categoria", "historial_categoria_alumno", "id_categoria"),
        ("ix_hist_equipo_usuario", "historial_equipo_alumno", "id_usuario"),
        ("ix_hist_equipo_equipo", "historial_equipo_alumno", "id_equipo"),
        ("ix_inscripcion_tarifa", "inscripcion_gestion", "id_tarifa"),
        ("ix_inscripcion_equipo", "inscripcion_gestion", "id_equipo_principal"),
        ("ix_inscripcion_categoria", "inscripcion_gestion", "id_categoria"),
        ("ix_movimiento_contable_sesion", "movimiento_contable", "id_sesion_caja"),
        ("ix_tarifa_categoria", "tarifa", "id_categoria"),
    ]
    for nombre, tabla, columna in indices:
        db.session.execute(text(f"CREATE INDEX IF NOT EXISTS {nombre} ON {tabla}({columna})"))
    db.session.commit()


def _migracion_30_permisos_asistencia_roles_operativos():
    db.session.execute(text("""INSERT OR IGNORE INTO rol_permiso(id_rol,id_permiso)
        SELECT r.id_rol,p.id_permiso FROM rol r JOIN permiso p ON p.codigo='gestionar_asistencia'
        WHERE r.nombre IN ('Secretaría','Profesor')"""))
    db.session.commit()


def _migracion_31_turno_entrenamiento_alumnos():
    if "turno" not in _columnas("alumno"):
        db.session.execute(text("ALTER TABLE alumno ADD COLUMN turno VARCHAR(10)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_alumno_turno ON alumno(turno)"))
    db.session.commit()


def _migracion_32_indices_partidos_origen():
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_partido_origen_local ON partido(id_partido_origen_local)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_partido_origen_visita ON partido(id_partido_origen_visita)"))
    db.session.commit()


def _migracion_33_ci_y_telefonos_numericos():
    if db.engine.dialect.name == "postgresql":
        restricciones = [
            ("alumno", "ci", "ck_alumno_ci_numerico"),
            ("alumno", "telefono", "ck_alumno_telefono_numerico"),
            ("tutor", "documento", "ck_tutor_documento_numerico"),
            ("tutor", "telefono", "ck_tutor_telefono_numerico"),
            ("personal_deportivo", "documento", "ck_personal_documento_numerico"),
            ("personal_deportivo", "telefono", "ck_personal_telefono_numerico"),
            ("proveedor", "documento", "ck_proveedor_documento_numerico"),
            ("proveedor", "telefono", "ck_proveedor_telefono_numerico"),
            ("configuracion", "telefono", "ck_configuracion_telefono_numerico"),
        ]
        for tabla, col, ck_name in restricciones:
            db.session.execute(text(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{ck_name}') THEN
                        ALTER TABLE {tabla} ADD CONSTRAINT {ck_name} CHECK ({col} IS NULL OR {col} ~ '^[0-9]+$');
                    END IF;
                END $$;
            """))
        db.session.commit()


MIGRACIONES = [
    (1, "Índices y restricciones únicas", _migracion_1_indices_integridad),
    (2, "Relación formal de equipo rival", _migracion_2_equipo_rival),
    (3, "Reparación y sincronización de Agenda", _migracion_3_reparar_agenda),
    (4, "Recálculo íntegro de tablas de posiciones", _migracion_4_recalcular_posiciones),
    (5, "Registro diferenciado de equipos rivales", _migracion_5_equipos_rivales),
    (6, "Catálogo reutilizable de canchas y lugares", _migracion_6_catalogo_lugares),
    (7, "Campeonatos avanzados, eliminatorias y convocatorias históricas", _migracion_7_campeonatos_avanzados),
    (8, "Integridad reforzada, auditoría, caja y configuración por categoría", _migracion_8_integridad_auditoria_y_caja),
    (9, "Reactivación de alumnos con nuevo ciclo de mensualidad", _migracion_9_reactivacion_alumnos),
    (10, "Endurecimiento operativo, lugares y ciclos", _migracion_10_endurecimiento_operativo),
    (11, "Enlace de Google Maps para canchas y lugares", _migracion_11_google_maps_lugares),
    (12, "Acceso local protegido por contraseña", _migracion_12_acceso_con_contrasena),
    (13, "Gestión configurable en ficha del alumno", _migracion_13_gestion_ficha),
    (14, "Marca genérica, contabilidad, inventario y ventas", _migracion_14_marca_contabilidad_inventario),
    (15, "Integridad reforzada e índices de rendimiento", _migracion_15_integridad_y_rendimiento),
    (16, "Índices completos para relaciones foráneas", _migracion_16_indices_foraneos_completos),
    (17, "Obligaciones y cuotas de pagos programados", _migracion_17_pagos_programados),
    (18, "Catálogo configurable de categorías contables", _migracion_18_categorias_contables),
    (19, "Usuarios, roles, permisos y auditoría por actor", _migracion_19_usuarios_roles_auditoria),
    (20, "Obligaciones, abonos parciales, tarifas y becas historicas", _migracion_20_obligaciones_y_abonos),
    (21, "Apertura, sesiones y movimientos de caja por usuario", _migracion_21_sesiones_caja),
    (22, "Compras formales e integridad cruzada", _migracion_22_compras_e_integridad_cruzada),
    (23, "Fuente deportiva unica y conflictos autorizados", _migracion_23_fuente_deportiva_y_conflictos),
    (24, "Inscripciones por gestion e historiales deportivos", _migracion_24_inscripciones_e_historiales),
    (25, "Categorias financieras por ID y proveedores ampliados", _migracion_25_catalogos_historicos),
    (26, "Personal deportivo, sesiones y asistencia", _migracion_26_personal_y_asistencia),
    (27, "Tutores, conteos fisicos y devoluciones", _migracion_27_tutores_conteos_devoluciones),
    (28, "Reparacion de relaciones de tutores", _migracion_28_reparar_relaciones_tutores),
    (29, "Indices y permisos operativos", _migracion_29_indices_y_permisos_operativos),
    (30, "Permisos de asistencia para roles operativos", _migracion_30_permisos_asistencia_roles_operativos),
    (31, "Turno de entrenamiento por alumno", _migracion_31_turno_entrenamiento_alumnos),
    (32, "Índices para llaves eliminatorias de partidos", _migracion_32_indices_partidos_origen),
    (33, "Restricción numérica para CI, documentos y teléfonos", _migracion_33_ci_y_telefonos_numericos),
]


def ejecutar_migraciones():
    aplicadas = _versiones_aplicadas()
    if not aplicadas and db.engine.dialect.name == "postgresql":
        tablas_existentes = set(inspect(db.engine).get_table_names())
        # Si las tablas más recientes ya existen en PostgreSQL por db.create_all(), registrar migraciones base
        if "obligacion" in tablas_existentes and "conteo_inventario" in tablas_existentes:
            for version, nombre, _ in MIGRACIONES:
                _registrar(version, nombre)
            return

    pendientes = [(version, nombre, funcion) for version, nombre, funcion in MIGRACIONES if version not in aplicadas]
    if pendientes:
        from flask import current_app
        from app.utils.backup import crear_respaldo
        respaldo = crear_respaldo(current_app, f"antes_migracion_v{pendientes[0][0]}_v{pendientes[-1][0]}")
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if uri.startswith("sqlite:///") and ":memory:" not in uri and respaldo is None:
            raise RuntimeError("No se pudo crear el respaldo obligatorio antes de migrar.")
    for version, nombre, funcion in pendientes:
        funcion()
        _registrar(version, nombre)
