from datetime import datetime
from app.extensions import db
from app.models import Entrenamiento, Auditoria


class ProgramarEntrenamientoUseCase:
    """Caso de uso: Programación de horarios y recurrencia de entrenamientos."""

    def ejecutar(self, datos, id_usuario=None):
        hora_inicio = datos["hora_inicio"]
        if isinstance(hora_inicio, str):
            hora_inicio = datetime.strptime(hora_inicio, "%H:%M").time()

        hora_fin = datos.get("hora_fin")
        if isinstance(hora_fin, str) and hora_fin.strip():
            hora_fin = datetime.strptime(hora_fin, "%H:%M").time()
        else:
            hora_fin = None

        entrenamiento = Entrenamiento(
            id_entrenador=int(datos["id_entrenador"]) if datos.get("id_entrenador") else None,
            dia_semana=int(datos["dia_semana"]),
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            lugar=datos.get("lugar", "").strip() or None,
            id_lugar=int(datos["id_lugar"]) if datos.get("id_lugar") else None,
            id_categoria=int(datos["id_categoria"]) if datos.get("id_categoria") else None,
            id_equipo=int(datos["id_equipo"]) if datos.get("id_equipo") else None,
            activo=True,
        )
        db.session.add(entrenamiento)
        db.session.flush()

        auditoria = Auditoria(
            modulo="Entrenamientos",
            accion="Crear entrenamiento",
            entidad="Entrenamiento",
            id_entidad=entrenamiento.id_entrenamiento,
            detalle=f"Se programó entrenamiento para día {entrenamiento.dia_semana} a las {hora_inicio}",
            id_usuario=id_usuario,
            valor_nuevo=f"Día {entrenamiento.dia_semana} {hora_inicio}",
        )
        db.session.add(auditoria)
        db.session.commit()

        return entrenamiento
