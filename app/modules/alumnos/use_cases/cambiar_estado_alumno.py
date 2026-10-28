from datetime import date
from app.extensions import db
from app.models import Alumno, Auditoria, HistorialAlumno


class CambiarEstadoAlumnoUseCase:
    """Caso de uso: Retiro o Reactivación deportiva de un alumno."""

    def retirar(self, id_alumno, motivo=None, id_usuario=None):
        alumno = Alumno.query.get_or_404(id_alumno)
        alumno.estado = "Retirado"
        alumno.fecha_retiro = date.today()

        hist = HistorialAlumno(
            id_alumno=alumno.id_alumno,
            tipo="Retiro",
            valor_anterior="Activo",
            valor_nuevo="Retirado",
            motivo=motivo or "Retiro solicitado",
        )
        db.session.add(hist)

        auditoria = Auditoria(
            modulo="Alumnos",
            accion="Retirar alumno",
            entidad="Alumno",
            id_entidad=alumno.id_alumno,
            detalle=f"Se retiró al alumno {alumno.nombre_completo}. Motivo: {motivo or 'N/A'}",
            id_usuario=id_usuario,
            valor_anterior="Activo",
            valor_nuevo="Retirado",
        )
        db.session.add(auditoria)
        db.session.commit()
        return alumno

    def reactivar(self, id_alumno, motivo=None, id_usuario=None):
        alumno = Alumno.query.get_or_404(id_alumno)
        alumno.estado = "Activo"
        alumno.fecha_retiro = None
        alumno.fecha_ultima_reactivacion = date.today()
        alumno.fecha_base_pago = date.today()

        hist = HistorialAlumno(
            id_alumno=alumno.id_alumno,
            tipo="Reactivación",
            valor_anterior="Retirado",
            valor_nuevo="Activo",
            motivo=motivo or "Reactivación de matrícula",
        )
        db.session.add(hist)

        auditoria = Auditoria(
            modulo="Alumnos",
            accion="Reactivar alumno",
            entidad="Alumno",
            id_entidad=alumno.id_alumno,
            detalle=f"Se reactivó al alumno {alumno.nombre_completo}",
            id_usuario=id_usuario,
            valor_anterior="Retirado",
            valor_nuevo="Activo",
        )
        db.session.add(auditoria)
        db.session.commit()
        return alumno
