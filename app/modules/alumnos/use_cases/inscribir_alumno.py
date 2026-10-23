from datetime import date, datetime
from app.extensions import db
from app.models import Alumno, Categoria, Equipo, InscripcionGestion, HistorialCategoriaAlumno, HistorialEquipoAlumno, Tutor, AlumnoTutor, Auditoria


class InscribirAlumnoUseCase:
    """Caso de uso: Inscripción de un nuevo alumno en la academia deportiva."""

    def ejecutar(self, datos, id_usuario=None):
        fecha_nac = datos.get("fecha_nacimiento")
        if isinstance(fecha_nac, str):
            fecha_nac = datetime.strptime(fecha_nac, "%Y-%m-%d").date()

        # Determinar categoría si no viene explícita o no es manual
        id_categoria = datos.get("id_categoria")
        categoria_manual = bool(datos.get("categoria_manual", False))

        if not id_categoria and fecha_nac and not categoria_manual:
            hoy = date.today()
            edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
            cat = Categoria.query.filter(
                (Categoria.edad_min <= edad) & (Categoria.edad_max >= edad)
            ).first()
            if cat:
                id_categoria = cat.id_categoria

        alumno = Alumno(
            nombre=datos["nombre"].strip(),
            apellido=datos["apellido"].strip(),
            id_categoria=id_categoria,
            categoria_manual=categoria_manual,
            fecha_nacimiento=fecha_nac,
            ci=datos.get("ci", "").strip() or None,
            direccion=datos.get("direccion", "").strip() or None,
            telefono=datos.get("telefono", "").strip() or None,
            tutor=datos.get("tutor", "").strip() or None,
            tutor2=datos.get("tutor2", "").strip() or None,
            sexo=datos.get("sexo") or None,
            posicion=datos.get("posicion") or None,
            pierna_habil=datos.get("pierna_habil") or None,
            peso=datos.get("peso") or None,
            estatura=datos.get("estatura") or None,
            beca=datos.get("beca", "Ninguna"),
            turno=datos.get("turno") or None,
            foto=datos.get("foto"),
            estado="Activo",
        )

        id_equipo = datos.get("id_equipo")
        if id_equipo:
            equipo = Equipo.query.get(id_equipo)
            if equipo:
                alumno.equipos.append(equipo)

        db.session.add(alumno)
        db.session.flush()

        # Registrar historial inicial de categoría
        if id_categoria:
            hist_cat = HistorialCategoriaAlumno(
                id_alumno=alumno.id_alumno,
                id_categoria=id_categoria,
                fecha_inicio=date.today(),
                tipo_asignacion="Manual" if categoria_manual else "Automática",
                motivo="Inscripción inicial",
                id_usuario=id_usuario,
            )
            db.session.add(hist_cat)

        # Registrar historial inicial de equipo
        if id_equipo:
            hist_eq = HistorialEquipoAlumno(
                id_alumno=alumno.id_alumno,
                id_equipo=id_equipo,
                gestion=date.today().year,
                fecha_inicio=date.today(),
                estado="Activa",
                principal=True,
                id_usuario=id_usuario,
            )
            db.session.add(hist_eq)

        # Registrar auditoría
        auditoria = Auditoria(
            modulo="Alumnos",
            accion="Crear alumno",
            entidad="Alumno",
            id_entidad=alumno.id_alumno,
            detalle=f"Se inscribió al alumno {alumno.nombre_completo}",
            id_usuario=id_usuario,
            valor_nuevo=alumno.nombre_completo,
        )
        db.session.add(auditoria)
        db.session.commit()

        return alumno
