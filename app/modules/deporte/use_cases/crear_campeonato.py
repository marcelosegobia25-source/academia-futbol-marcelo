from datetime import date, datetime
from app.extensions import db
from app.models import Campeonato, Categoria, Equipo, Auditoria


class CrearCampeonatoUseCase:
    """Caso de uso: Creación y configuración de un nuevo campeonato deportivo."""

    def ejecutar(self, datos, id_usuario=None):
        fecha_inicio = datos["fecha_inicio"]
        if isinstance(fecha_inicio, str):
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()

        fecha_fin = datos.get("fecha_fin")
        if isinstance(fecha_fin, str):
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date() if fecha_fin else None

        campeonato = Campeonato(
            nombre=datos["nombre"].strip(),
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            lugar=datos.get("lugar", "").strip() or None,
            id_lugar=int(datos["id_lugar"]) if datos.get("id_lugar") else None,
            formato=datos.get("formato", "Liga"),
            vueltas=int(datos.get("vueltas", 1)),
            clasificados=int(datos.get("clasificados", 4)),
            tercer_puesto=bool(datos.get("tercer_puesto", False)),
            estado="Planificado",
        )

        categorias_ids = datos.get("categorias", [])
        if categorias_ids:
            campeonato.categorias = Categoria.query.filter(Categoria.id_categoria.in_(categorias_ids)).all()

        equipos_ids = datos.get("equipos", [])
        if equipos_ids:
            campeonato.equipos = Equipo.query.filter(Equipo.id_equipo.in_(equipos_ids)).all()

        db.session.add(campeonato)
        db.session.flush()

        auditoria = Auditoria(
            modulo="Campeonatos",
            accion="Crear campeonato",
            entidad="Campeonato",
            id_entidad=campeonato.id_campeonato,
            detalle=f"Se creó el campeonato {campeonato.nombre} (Formato: {campeonato.formato})",
            id_usuario=id_usuario,
            valor_nuevo=campeonato.nombre,
        )
        db.session.add(auditoria)
        db.session.commit()

        return campeonato
