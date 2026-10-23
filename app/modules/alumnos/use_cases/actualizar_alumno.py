from datetime import date, datetime
from app.extensions import db
from app.models import Alumno, Equipo, HistorialAlumno, HistorialCategoriaAlumno, HistorialEquipoAlumno, Auditoria


class ActualizarAlumnoUseCase:
    """Caso de uso: Modificación de datos y seguimiento de cambios de un alumno."""

    def ejecutar(self, id_alumno, datos, id_usuario=None):
        alumno = Alumno.query.get_or_404(id_alumno)

        cambios = []
        antiguo_nombre = alumno.nombre_completo

        for campo in ["nombre", "apellido", "direccion", "telefono", "tutor", "tutor2", "posicion", "pierna_habil", "turno"]:
            if campo in datos:
                val = (datos[campo] or "").strip() or None
                actual = getattr(alumno, campo)
                if val != actual:
                    cambios.append((campo, actual, val))
                    setattr(alumno, campo, val)

        for campo in ["peso", "estatura"]:
            if campo in datos:
                val = float(datos[campo]) if datos[campo] else None
                actual = getattr(alumno, campo)
                if val != actual:
                    cambios.append((campo, actual, val))
                    setattr(alumno, campo, val)

        if "beca" in datos:
            val = datos["beca"]
            if val != alumno.beca:
                cambios.append(("beca", alumno.beca, val))
                alumno.beca = val

        # Cambio de Categoría
        if "id_categoria" in datos:
            nueva_cat = int(datos["id_categoria"]) if datos["id_categoria"] else None
            cat_manual = bool(datos.get("categoria_manual", False))
            if nueva_cat != alumno.id_categoria:
                # Cerrar historial anterior
                anterior_hist = HistorialCategoriaAlumno.query.filter_by(
                    id_alumno=alumno.id_alumno, fecha_fin=None
                ).first()
                if anterior_hist:
                    anterior_hist.fecha_fin = date.today()

                if nueva_cat:
                    nuevo_hist = HistorialCategoriaAlumno(
                        id_alumno=alumno.id_alumno,
                        id_categoria=nueva_cat,
                        fecha_inicio=date.today(),
                        tipo_asignacion="Manual" if cat_manual else "Automática",
                        motivo=datos.get("motivo_categoria", "Actualización de ficha"),
                        id_usuario=id_usuario,
                    )
                    db.session.add(nuevo_hist)
                alumno.id_categoria = nueva_cat
                alumno.categoria_manual = cat_manual
                cambios.append(("id_categoria", alumno.id_categoria, nueva_cat))

        # Registrar historial de cambios en ficha
        for campo, anterior, nuevo in cambios:
            hist = HistorialAlumno(
                id_alumno=alumno.id_alumno,
                tipo=f"Edición {campo}",
                valor_anterior=str(anterior) if anterior else None,
                valor_nuevo=str(nuevo) if nuevo else None,
                motivo="Modificación desde perfil",
            )
            db.session.add(hist)

        auditoria = Auditoria(
            modulo="Alumnos",
            accion="Editar alumno",
            entidad="Alumno",
            id_entidad=alumno.id_alumno,
            detalle=f"Se actualizó la ficha de {alumno.nombre_completo}",
            id_usuario=id_usuario,
            valor_anterior=antiguo_nombre,
            valor_nuevo=alumno.nombre_completo,
        )
        db.session.add(auditoria)
        db.session.commit()

        return alumno
