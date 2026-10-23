from datetime import datetime
from app.extensions import db
from app.models import Partido, Posicion, Campeonato, Auditoria


class RegistrarResultadoPartidoUseCase:
    """Caso de uso: Carga de resultados de un partido y actualización de posiciones/llaves."""

    def ejecutar(self, id_partido, goles_local, goles_visita, estado="Finalizado", observacion=None, penales_local=None, penales_visita=None, id_usuario=None):
        partido = Partido.query.get_or_404(id_partido)

        partido.goles_local = int(goles_local) if goles_local is not None else None
        partido.goles_visita = int(goles_visita) if goles_visita is not None else None
        partido.penales_local = int(penales_local) if penales_local is not None else None
        partido.penales_visita = int(penales_visita) if penales_visita is not None else None
        partido.estado_partido = estado
        if observacion is not None:
            partido.observacion = observacion

        if partido.goles_local is not None and partido.goles_visita is not None:
            partido.resultado = f"{partido.goles_local}-{partido.goles_visita}"

        # Actualizar tabla de posiciones si es fase de Liga
        if partido.id_campeonato and partido.fase in ["Liga", "Grupos"]:
            self._actualizar_tabla_posiciones(partido)

        # Si es eliminatoria y tiene partidos siguientes vinculados, avanzar ganador
        ganador_id = partido.ganador_id
        if ganador_id and partido.es_eliminatorio:
            self._avanzar_en_llave(partido, ganador_id)

        auditoria = Auditoria(
            modulo="Partidos",
            accion="Registrar resultado",
            entidad="Partido",
            id_entidad=partido.id_partido,
            detalle=f"Resultado {partido.equipo.nombre} vs {partido.rival}: {partido.resultado} ({estado})",
            id_usuario=id_usuario,
            valor_nuevo=partido.resultado,
        )
        db.session.add(auditoria)
        db.session.commit()

        return partido

    def _actualizar_tabla_posiciones(self, partido):
        # Recalcular las posiciones de los dos equipos
        for eq_id in [partido.id_equipo, partido.id_equipo_rival]:
            if not eq_id:
                continue
            pos = Posicion.query.filter_by(
                id_campeonato=partido.id_campeonato,
                id_categoria=partido.id_categoria,
                id_equipo=eq_id
            ).first()
            if not pos:
                pos = Posicion(
                    id_campeonato=partido.id_campeonato,
                    id_categoria=partido.id_categoria,
                    id_equipo=eq_id
                )
                db.session.add(pos)

            # Contabilizar todos los partidos finalizados
            partidos_eq = Partido.query.filter(
                Partido.id_campeonato == partido.id_campeonato,
                Partido.id_categoria == partido.id_categoria,
                Partido.estado_partido.in_(["Finalizado", "Walkover"]),
                (Partido.id_equipo == eq_id) | (Partido.id_equipo_rival == eq_id)
            ).all()

            pj = len(partidos_eq)
            pg = pe = pp = gf = gc = 0
            for p in partidos_eq:
                if p.goles_local is None or p.goles_visita is None:
                    continue
                es_local = (p.id_equipo == eq_id)
                g_favor = p.goles_local if es_local else p.goles_visita
                g_contra = p.goles_visita if es_local else p.goles_local
                gf += g_favor
                gc += g_contra
                if g_favor > g_contra:
                    pg += 1
                elif g_favor == g_contra:
                    pe += 1
                else:
                    pp += 1

            pos.pj = pj
            pos.pg = pg
            pos.pe = pe
            pos.pp = pp
            pos.gf = gf
            pos.gc = gc

    def _avanzar_en_llave(self, partido, ganador_id):
        # Buscar partidos que tengan a este como origen
        siguiente_local = Partido.query.filter_by(id_partido_origen_local=partido.id_partido).first()
        if siguiente_local:
            siguiente_local.id_equipo = ganador_id

        siguiente_visita = Partido.query.filter_by(id_partido_origen_visita=partido.id_partido).first()
        if siguiente_visita:
            siguiente_visita.id_equipo_rival = ganador_id
            from app.models import Equipo
            eq = Equipo.query.get(ganador_id)
            if eq:
                siguiente_visita.rival = eq.nombre
