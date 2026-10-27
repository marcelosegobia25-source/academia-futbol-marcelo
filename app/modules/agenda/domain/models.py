from datetime import date, datetime, timezone
from sqlalchemy.orm import validates
from app.extensions import db
from app.utils.validacion import solo_numeros_opcional


def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EventoAgenda(db.Model):
    __tablename__ = "evento_agenda"
    __table_args__ = (
        db.CheckConstraint("tipo IN ('Evento','Partido','Entrenamiento')", name="ck_evento_tipo"),
    )
    id_evento = db.Column(db.Integer, primary_key=True)
    hora = db.Column(db.Time, nullable=True)
    fecha = db.Column(db.Date, nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    lugar = db.Column(db.String(150), nullable=True)
    id_lugar = db.Column(
        db.Integer, db.ForeignKey("lugar.id_lugar", ondelete="SET NULL"), nullable=True
    )
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo"), nullable=True)
    tipo = db.Column(db.String(20), default="Evento")
    id_partido = db.Column(db.Integer, db.ForeignKey("partido.id_partido"), nullable=True)

    categoria = db.relationship("Categoria")
    equipo = db.relationship("Equipo")
    partido = db.relationship("Partido")
    lugar_catalogo = db.relationship("Lugar")

    @property
    def id_entrenamiento(self):
        return None

    @property
    def hora_fin(self):
        return None


class Entrenamiento(db.Model):
    """Entrenamientos fijos (recurrentes semanalmente) que se muestran en el calendario."""
    __tablename__ = "entrenamiento"
    __table_args__ = (
        db.CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_entrenamiento_dia"),
        db.CheckConstraint("hora_fin IS NULL OR hora_fin > hora_inicio", name="ck_entrenamiento_horas"),
        db.CheckConstraint("fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio", name="ck_entrenamiento_fechas"),
    )
    id_entrenamiento = db.Column(db.Integer, primary_key=True)
    id_entrenador = db.Column(db.Integer, db.ForeignKey("personal_deportivo.id_personal", ondelete="SET NULL"), nullable=True)
    dia_semana = db.Column(db.Integer, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=True)
    lugar = db.Column(db.String(150), nullable=True)
    id_lugar = db.Column(
        db.Integer, db.ForeignKey("lugar.id_lugar", ondelete="SET NULL"), nullable=True
    )
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo"), nullable=True)
    activo = db.Column(db.Boolean, default=True)

    categoria = db.relationship("Categoria")
    equipo = db.relationship("Equipo")
    lugar_catalogo = db.relationship("Lugar")
    entrenador = db.relationship("PersonalDeportivo", backref="entrenamientos")

    @property
    def turno(self):
        if self.hora_inicio.hour < 12:
            return "Mañana"
        if self.hora_inicio.hour < 18:
            return "Tarde"
        return "Noche"


class PersonalDeportivo(db.Model):
    __tablename__ = "personal_deportivo"
    id_personal = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    documento = db.Column(db.String(40), nullable=True, unique=True)
    telefono = db.Column(db.String(40), nullable=True)
    correo = db.Column(db.String(120), nullable=True)
    especialidad = db.Column(db.String(120), nullable=True)
    tipo = db.Column(db.String(20), nullable=False, default="Entrenador")
    fecha_ingreso = db.Column(db.Date, nullable=False, default=date.today)
    fecha_salida = db.Column(db.Date, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    observacion = db.Column(db.String(255), nullable=True)

    @validates("documento")
    def _validar_documento(self, key, valor):
        return solo_numeros_opcional(valor, "Documento", 40)

    @validates("telefono")
    def _validar_telefono(self, key, valor):
        return solo_numeros_opcional(valor, "Teléfono", 40)



class SesionEntrenamiento(db.Model):
    __tablename__ = "sesion_entrenamiento"
    __table_args__ = (db.UniqueConstraint("id_entrenamiento", "fecha", name="uq_sesion_entrenamiento_fecha"),)
    id_sesion_entrenamiento = db.Column(db.Integer, primary_key=True)
    id_entrenamiento = db.Column(db.Integer, db.ForeignKey("entrenamiento.id_entrenamiento", ondelete="CASCADE"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(12), nullable=False, default="Programada")
    observacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    entrenamiento = db.relationship("Entrenamiento", backref=db.backref("sesiones", cascade="all, delete-orphan", passive_deletes=True, order_by="desc(SesionEntrenamiento.fecha)"))


class AsistenciaEntrenamiento(db.Model):
    __tablename__ = "asistencia_entrenamiento"
    __table_args__ = (db.UniqueConstraint("id_sesion_entrenamiento", "id_alumno", name="uq_asistencia_sesion_alumno"),)
    id_asistencia = db.Column(db.Integer, primary_key=True)
    id_sesion_entrenamiento = db.Column(db.Integer, db.ForeignKey("sesion_entrenamiento.id_sesion_entrenamiento", ondelete="CASCADE"), nullable=False)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="RESTRICT"), nullable=False)
    estado = db.Column(db.String(12), nullable=False, default="Presente")
    justificacion = db.Column(db.String(255), nullable=True)
    registrado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    sesion = db.relationship("SesionEntrenamiento", backref=db.backref("asistencias", cascade="all, delete-orphan"))
    alumno = db.relationship("Alumno", backref="asistencias_entrenamiento")


class ConflictoAutorizado(db.Model):
    __tablename__ = "conflicto_autorizado"
    id_conflicto = db.Column(db.Integer, primary_key=True)
    tipo_entidad = db.Column(db.String(30), nullable=False)
    id_entidad = db.Column(db.Integer, nullable=False)
    tipo_conflicto = db.Column(db.String(40), nullable=False)
    referencia = db.Column(db.String(120), nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    usuario = db.relationship("Usuario")
