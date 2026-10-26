from datetime import date, datetime, timezone
from sqlalchemy.orm import validates
from app.extensions import db
from app.utils.validacion import solo_numeros_opcional


def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --------------------------------------------------------------------------
# Tabla de asociación Alumno - Equipo y Constantes del Dominio
# --------------------------------------------------------------------------

ESTADOS_ALUMNO = ["Activo", "Retirado"]
POSICIONES = ["DEL", "DEF", "MED", "POR"]
PIERNAS = ["Izquierda", "Derecha", "Ambas"]
SEXOS = ["M", "F"]
BECAS = ["Ninguna", "Media", "Completa"]
TURNOS = ["Mañana", "Tarde", "Noche"]

alumno_equipo = db.Table(
    "alumno_equipo",
    db.Column("id_alumno", db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="CASCADE"), primary_key=True),
    db.Column("id_equipo", db.Integer, db.ForeignKey("equipo.id_equipo", ondelete="CASCADE"), primary_key=True),
)


class Alumno(db.Model):
    __tablename__ = "alumno"
    __table_args__ = (
        db.Index(
            "uq_alumno_ci",
            "ci",
            unique=True,
            sqlite_where=db.text("ci IS NOT NULL AND trim(ci) <> ''"),
            postgresql_where=db.text("ci IS NOT NULL AND trim(ci) <> ''"),
        ),
        db.CheckConstraint("estado IN ('Activo','Retirado')", name="ck_alumno_estado"),
        db.CheckConstraint("sexo IS NULL OR sexo IN ('M','F')", name="ck_alumno_sexo"),
        db.CheckConstraint(
            "posicion IS NULL OR posicion IN ('DEL','DEF','MED','POR')",
            name="ck_alumno_posicion",
        ),
        db.CheckConstraint(
            "pierna_habil IS NULL OR pierna_habil IN ('Izquierda','Derecha','Ambas')",
            name="ck_alumno_pierna",
        ),
        db.CheckConstraint(
            "beca IN ('Ninguna','Media','Completa')",
            name="ck_alumno_beca",
        ),
        db.CheckConstraint(
            "turno IS NULL OR turno IN ('Mañana','Tarde','Noche')",
            name="ck_alumno_turno",
        ),
        db.CheckConstraint("peso IS NULL OR peso > 0", name="ck_alumno_peso"),
        db.CheckConstraint("estatura IS NULL OR estatura > 0", name="ck_alumno_estatura"),
    )
    id_alumno = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=True)
    categoria_manual = db.Column(db.Boolean, default=False)
    foto = db.Column(db.String(255), nullable=True)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    ci = db.Column(db.String(30), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    tutor = db.Column(db.String(120), nullable=True)
    tutor2 = db.Column(db.String(120), nullable=True)
    telefono = db.Column(db.String(30), nullable=True)
    estado = db.Column(db.String(20), default="Activo")
    posicion = db.Column(db.String(5), nullable=True)
    pierna_habil = db.Column(db.String(15), nullable=True)
    peso = db.Column(db.Float, nullable=True)
    estatura = db.Column(db.Float, nullable=True)
    sexo = db.Column(db.String(1), nullable=True)
    beca = db.Column(db.String(15), default="Ninguna")
    turno = db.Column(db.String(10), nullable=True, index=True)
    beca_fecha_fin = db.Column(db.Date, nullable=True)

    fecha_base_pago = db.Column(db.Date, nullable=True)
    fecha_ultima_reactivacion = db.Column(db.Date, nullable=True)
    fecha_retiro = db.Column(db.Date, nullable=True)

    creado_en = db.Column(db.DateTime, default=ahora_utc)

    equipos = db.relationship("Equipo", secondary=alumno_equipo, back_populates="alumnos")
    pagos = db.relationship(
        "Pago", backref="alumno", lazy=True,
        order_by="Pago.fecha_pago.desc(), Pago.hora_registro.desc(), Pago.id_pago.desc()",
    )
    campeonatos_habilitados = db.relationship(
        "AlumnoCampeonato", backref="alumno", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    @property
    def codigo_interno(self):
        return f"ALU-{self.id_alumno:06d}" if self.id_alumno else "ALU-NUEVO"

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        años = hoy.year - self.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day):
            años -= 1
        return años

    @property
    def ultimos_6_pagos(self):
        return self.pagos[:6]

    @property
    def ultimo_pago(self):
        mes_inicio = (
            self.fecha_ultima_reactivacion.strftime("%Y-%m")
            if self.fecha_ultima_reactivacion else None
        )
        activos = [
            p for p in self.pagos
            if p.eliminado_en is None
            and (p.aplicacion is None or p.aplicacion.obligacion.saldo <= 0)
            and (mes_inicio is None or p.mes_pagado >= mes_inicio)
        ]
        return max(
            activos,
            key=lambda p: (p.fecha_vencimiento, p.mes_pagado, p.creado_en or datetime.min),
            default=None,
        )

    @property
    def estado_mensualidad(self):
        if self.estado == "Retirado":
            return "Retirado"
        ultimo = self.ultimo_pago
        if ultimo is None:
            return "Sin pagos"
        return ultimo.estado_cobertura

    @property
    def campeonatos_activos(self):
        return [ac.campeonato.nombre for ac in self.campeonatos_habilitados if ac.habilitado]

    @property
    def beca_vigente(self):
        if self.beca_fecha_fin and self.beca_fecha_fin < date.today():
            return "Ninguna"
        return self.beca or "Ninguna"

    @validates("ci")
    def _validar_ci(self, key, valor):
        return solo_numeros_opcional(valor, "CI", 30)

    @validates("telefono")
    def _validar_telefono(self, key, valor):
        return solo_numeros_opcional(valor, "Teléfono", 30)

    def __repr__(self):
        return f"<Alumno {self.nombre_completo}>"


class Tutor(db.Model):
    __tablename__ = "tutor"
    id_tutor = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    documento = db.Column(db.String(40), nullable=True)
    telefono = db.Column(db.String(40), nullable=True)
    correo = db.Column(db.String(120), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    @validates("documento")
    def _validar_documento(self, key, valor):
        return solo_numeros_opcional(valor, "Documento", 40)

    @validates("telefono")
    def _validar_telefono(self, key, valor):
        return solo_numeros_opcional(valor, "Teléfono", 40)



class AlumnoTutor(db.Model):
    __tablename__ = "alumno_tutor"
    __table_args__ = (db.UniqueConstraint("id_alumno", "id_tutor", name="uq_alumno_tutor"),)
    id_alumno_tutor = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="CASCADE"), nullable=False)
    id_tutor = db.Column(db.Integer, db.ForeignKey("tutor.id_tutor", ondelete="RESTRICT"), nullable=False)
    parentesco = db.Column(db.String(30), nullable=True)
    principal = db.Column(db.Boolean, nullable=False, default=False)
    autorizado_recoger = db.Column(db.Boolean, nullable=False, default=True)
    alumno = db.relationship("Alumno", backref=db.backref("tutores_rel", cascade="all, delete-orphan"))
    tutor = db.relationship("Tutor", backref="alumnos_rel")


class BecaHistorial(db.Model):
    __tablename__ = "beca_historial"
    id_beca = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="RESTRICT"), nullable=False)
    porcentaje = db.Column(db.Numeric(5, 2), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    motivo = db.Column(db.String(255), nullable=True)
    autorizado_por = db.Column(db.String(120), nullable=True)
    estado = db.Column(db.String(12), nullable=False, default="Activa")
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    alumno = db.relationship("Alumno", backref=db.backref("historial_becas", lazy=True))


class InscripcionGestion(db.Model):
    __tablename__ = "inscripcion_gestion"
    __table_args__ = (
        db.UniqueConstraint("id_alumno", "gestion", name="uq_inscripcion_alumno_gestion"),
        db.CheckConstraint("porcentaje_beca >= 0 AND porcentaje_beca <= 100", name="ck_inscripcion_beca"),
    )
    id_inscripcion = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="RESTRICT"), nullable=False)
    gestion = db.Column(db.Integer, nullable=False)
    fecha_inscripcion = db.Column(db.Date, nullable=False, default=date.today)
    fecha_fin = db.Column(db.Date, nullable=True)
    estado = db.Column(db.String(15), nullable=False, default="Activa")
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria", ondelete="SET NULL"), nullable=True)
    id_equipo_principal = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo", ondelete="SET NULL"), nullable=True)
    id_tarifa = db.Column(db.Integer, db.ForeignKey("tarifa.id_tarifa", ondelete="SET NULL"), nullable=True)
    monto_tarifa = db.Column(db.Numeric(10, 2), nullable=True)
    porcentaje_beca = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    observacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    alumno = db.relationship("Alumno", backref=db.backref("inscripciones", order_by="desc(InscripcionGestion.gestion)"))
    categoria = db.relationship("Categoria")
    equipo_principal = db.relationship("Equipo")
    tarifa = db.relationship("Tarifa")


class HistorialCategoriaAlumno(db.Model):
    __tablename__ = "historial_categoria_alumno"
    id_historial_categoria = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="RESTRICT"), nullable=False)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria", ondelete="RESTRICT"), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    tipo_asignacion = db.Column(db.String(10), nullable=False, default="Automática")
    motivo = db.Column(db.String(255), nullable=True)
    bloqueada_hasta = db.Column(db.Date, nullable=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True)
    migrado_sin_fecha = db.Column(db.Boolean, nullable=False, default=False)
    alumno = db.relationship("Alumno", backref=db.backref("historial_categorias", order_by="desc(HistorialCategoriaAlumno.fecha_inicio)"))
    categoria = db.relationship("Categoria")


class HistorialEquipoAlumno(db.Model):
    __tablename__ = "historial_equipo_alumno"
    id_historial_equipo = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="RESTRICT"), nullable=False)
    id_equipo = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo", ondelete="RESTRICT"), nullable=False)
    gestion = db.Column(db.Integer, nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    estado = db.Column(db.String(12), nullable=False, default="Activa")
    motivo_salida = db.Column(db.String(255), nullable=True)
    principal = db.Column(db.Boolean, nullable=False, default=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True)
    migrado_sin_fecha = db.Column(db.Boolean, nullable=False, default=False)
    alumno = db.relationship("Alumno", backref=db.backref("historial_equipos", order_by="desc(HistorialEquipoAlumno.fecha_inicio)"))
    equipo = db.relationship("Equipo")


class HistorialAlumno(db.Model):
    """Trazabilidad de cambios relevantes de la ficha deportiva."""
    __tablename__ = "historial_alumno"
    id_historial = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(
        db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="CASCADE"), nullable=False
    )
    tipo = db.Column(db.String(40), nullable=False)
    valor_anterior = db.Column(db.Text, nullable=True)
    valor_nuevo = db.Column(db.Text, nullable=True)
    motivo = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    alumno = db.relationship("Alumno", backref=db.backref(
        "historial", order_by="desc(HistorialAlumno.creado_en)", cascade="all, delete-orphan"
    ))
