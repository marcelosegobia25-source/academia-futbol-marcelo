"""Motor común de conflictos para partidos, agenda y entrenamientos offline."""
from datetime import datetime, timedelta
from app.models import Entrenamiento, EventoAgenda, Partido


def _intervalo(fecha, hora, minutos):
    if not fecha or not hora:
        return None
    inicio = datetime.combine(fecha, hora)
    return inicio, inicio + timedelta(minutes=minutos)


def _solapa(a, b):
    return bool(a and b and a[0] < b[1] and a[1] > b[0])


def detectar_conflictos(fecha, hora, id_lugar=None, nombre_lugar=None,
                        id_equipo=None, id_equipo_rival=None,
                        excluir_partido=None, excluir_evento=None,
                        duracion_minutos=90):
    actual = _intervalo(fecha, hora, duracion_minutos)
    if not actual:
        return []
    hallazgos = []
    lugar_normalizado = (nombre_lugar or "").strip().lower()
    equipos = {x for x in (id_equipo, id_equipo_rival) if x}

    for partido in Partido.query.filter(Partido.fecha == fecha, Partido.estado_partido != "Cancelado").all():
        if partido.id_partido == excluir_partido or not _solapa(actual, _intervalo(partido.fecha, partido.hora, 90)):
            continue
        mismo_lugar = (id_lugar and partido.id_lugar == id_lugar) or (
            not id_lugar and lugar_normalizado and (partido.cancha or "").strip().lower() == lugar_normalizado)
        equipos_partido = {x for x in (partido.id_equipo, partido.id_equipo_rival) if x}
        if mismo_lugar:
            hallazgos.append(("Cancha ocupada", f"Partido #{partido.id_partido}"))
        if equipos & equipos_partido:
            hallazgos.append(("Equipo ocupado", f"Partido #{partido.id_partido}"))

    for evento in EventoAgenda.query.filter(EventoAgenda.fecha == fecha, EventoAgenda.tipo != "Partido").all():
        if evento.id_evento == excluir_evento or not _solapa(actual, _intervalo(evento.fecha, evento.hora, 60)):
            continue
        mismo_lugar = (id_lugar and evento.id_lugar == id_lugar) or (
            not id_lugar and lugar_normalizado and (evento.lugar or "").strip().lower() == lugar_normalizado)
        if mismo_lugar:
            hallazgos.append(("Lugar ocupado", f"Evento #{evento.id_evento}"))
        if evento.id_equipo and evento.id_equipo in equipos:
            hallazgos.append(("Equipo ocupado", f"Evento #{evento.id_evento}"))

    for entrenamiento in Entrenamiento.query.filter_by(dia_semana=fecha.weekday(), activo=True).all():
        if entrenamiento.fecha_inicio and fecha < entrenamiento.fecha_inicio:
            continue
        if entrenamiento.fecha_fin and fecha > entrenamiento.fecha_fin:
            continue
        fin = entrenamiento.hora_fin or (datetime.combine(fecha, entrenamiento.hora_inicio) + timedelta(minutes=60)).time()
        if not _solapa(actual, (_intervalo(fecha, entrenamiento.hora_inicio, 1)[0], datetime.combine(fecha, fin))):
            continue
        mismo_lugar = (id_lugar and entrenamiento.id_lugar == id_lugar) or (
            not id_lugar and lugar_normalizado and (entrenamiento.lugar or "").strip().lower() == lugar_normalizado)
        if mismo_lugar:
            hallazgos.append(("Lugar ocupado", f"Entrenamiento #{entrenamiento.id_entrenamiento}"))
        if entrenamiento.id_equipo and entrenamiento.id_equipo in equipos:
            hallazgos.append(("Equipo ocupado", f"Entrenamiento #{entrenamiento.id_entrenamiento}"))
    return list(dict.fromkeys(hallazgos))


def es_duplicado_partido(fecha, hora, id_equipo, id_equipo_rival, rival, excluir=None):
    consulta = Partido.query.filter_by(fecha=fecha, hora=hora, id_equipo=id_equipo)
    if excluir:
        consulta = consulta.filter(Partido.id_partido != excluir)
    for partido in consulta.all():
        mismo_rival = id_equipo_rival and partido.id_equipo_rival == id_equipo_rival
        mismo_nombre = (partido.rival or "").strip().lower() == (rival or "").strip().lower()
        if mismo_rival or mismo_nombre:
            return partido
    return None
