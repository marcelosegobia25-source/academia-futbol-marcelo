from datetime import datetime, timezone
from app.extensions import db


def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --------------------------------------------------------------------------
# Tablas de asociación N:M
# --------------------------------------------------------------------------

campeonato_categoria = db.Table(
    "campeonato_categoria",
    db.Column("id_campeonato", db.Integer, db.ForeignKey("campeonato.id_campeonato", ondelete="CASCADE"), primary_key=True),
    db.Column("id_categoria", db.Integer, db.ForeignKey("categoria.id_categoria", ondelete="RESTRICT"), primary_key=True),
)

campeonato_equipo = db.Table(
    "campeonato_equipo",
    db.Column("id_campeonato", db.Integer, db.ForeignKey("campeonato.id_campeonato", ondelete="CASCADE"), primary_key=True),
    db.Column("id_equipo", db.Integer, db.ForeignKey("equipo.id_equipo", ondelete="RESTRICT"), primary_key=True),
)


class Categoria(db.Model):
    __tablename__ = "categoria"
    __table_args__ = (
        db.CheckConstraint(
            "edad_min IS NULL OR edad_max IS NULL OR edad_min <= edad_max",
            name="ck_categoria_rango_edad",
        ),
        db.CheckConstraint("edad_min IS NULL OR edad_min >= 0", name="ck_categoria_edad_min"),
        db.CheckConstraint("edad_max IS NULL OR edad_max >= 0", name="ck_categoria_edad_max"),
    )
    id_categoria = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False, unique=True)
    edad_min = db.Column(db.Integer, nullable=True)
    edad_max = db.Column(db.Integer, nullable=True)

    equipos = db.relationship("Equipo", backref="categoria", lazy=True)
    alumnos = db.relationship("Alumno", backref="categoria", lazy=True)

    @property
    def nombre_mostrado(self):
        return f"Sub {self.nombre}" if self.nombre.isdigit() else self.nombre

    def __repr__(self):
        return f"<Categoria {self.nombre}>"


class Equipo(db.Model):
    __tablename__ = "equipo"
    __table_args__ = (
        db.Index("ix_equipo_nombre_categoria", "nombre", "id_categoria"),
        db.UniqueConstraint(
            "nombre", "id_categoria", "es_rival",
            name="uq_equipo_nombre_categoria_tipo",
        ),
    )
    id_equipo = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=True)
    es_rival = db.Column(db.Boolean, nullable=False, default=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    alumnos = db.relationship("Alumno", secondary="alumno_equipo", back_populates="equipos")

    def __repr__(self):
        tipo = "Rival" if self.es_rival else "Equipo"
        return f"<{tipo} {self.nombre}>"


class Partido(db.Model):
    __tablename__ = "partido"
    __table_args__ = (
        db.CheckConstraint(
            "id_equipo_rival IS NULL OR id_equipo <> id_equipo_rival",
            name="ck_partido_equipos_distintos",
        ),
        db.CheckConstraint("goles_local IS NULL OR goles_local >= 0", name="ck_partido_goles_local"),
        db.CheckConstraint("goles_visita IS NULL OR goles_visita >= 0", name="ck_partido_goles_visita"),
        db.CheckConstraint("penales_local IS NULL OR penales_local >= 0", name="ck_partido_penales_local"),
        db.CheckConstraint("penales_visita IS NULL OR penales_visita >= 0", name="ck_partido_penales_visita"),
        db.CheckConstraint(
            "fase IN ('Liga','Grupos','Cuartos','Semifinal','Final','Tercer puesto')",
            name="ck_partido_fase",
        ),
        db.CheckConstraint(
            "estado_partido IN ('Programado','Finalizado','Suspendido','Reprogramado','Cancelado','Walkover')",
            name="ck_partido_estado",
        ),
    )
    id_partido = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=True)
    cancha = db.Column(db.String(150), nullable=True)
    id_lugar = db.Column(
        db.Integer, db.ForeignKey("lugar.id_lugar", ondelete="SET NULL"), nullable=True
    )
    resultado = db.Column(db.String(30), nullable=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo"), nullable=False)
    id_equipo_rival = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo"), nullable=True)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=False)
    rival = db.Column(db.String(150), nullable=False)
    id_campeonato = db.Column(db.Integer, db.ForeignKey("campeonato.id_campeonato"), nullable=True)
    fase = db.Column(db.String(30), nullable=False, default="Liga")
    grupo = db.Column(db.String(30), nullable=True)
    jornada = db.Column(db.Integer, nullable=True)
    orden_llave = db.Column(db.Integer, nullable=True)
    estado_partido = db.Column(db.String(20), nullable=False, default="Programado")
    goles_local = db.Column(db.Integer, nullable=True)
    goles_visita = db.Column(db.Integer, nullable=True)
    penales_local = db.Column(db.Integer, nullable=True)
    penales_visita = db.Column(db.Integer, nullable=True)
    observacion = db.Column(db.String(255), nullable=True)
    id_partido_origen_local = db.Column(db.Integer, db.ForeignKey("partido.id_partido"), nullable=True, index=True)
    id_partido_origen_visita = db.Column(db.Integer, db.ForeignKey("partido.id_partido"), nullable=True, index=True)

    equipo = db.relationship("Equipo", foreign_keys=[id_equipo])
    equipo_rival = db.relationship("Equipo", foreign_keys=[id_equipo_rival])
    categoria = db.relationship("Categoria")
    campeonato = db.relationship("Campeonato")
    lugar_catalogo = db.relationship("Lugar")
    origen_local = db.relationship("Partido", remote_side=[id_partido], foreign_keys=[id_partido_origen_local])
    origen_visita = db.relationship("Partido", remote_side=[id_partido], foreign_keys=[id_partido_origen_visita])

    @property
    def es_eliminatorio(self):
        return self.fase in {"Cuartos", "Semifinal", "Final", "Tercer puesto"}

    @property
    def ganador_id(self):
        if self.estado_partido not in {"Finalizado", "Walkover"} or self.goles_local is None or self.goles_visita is None:
            return None
        if self.goles_local > self.goles_visita:
            return self.id_equipo
        if self.goles_visita > self.goles_local:
            return self.id_equipo_rival
        if self.penales_local is not None and self.penales_visita is not None:
            if self.penales_local > self.penales_visita:
                return self.id_equipo
            if self.penales_visita > self.penales_local:
                return self.id_equipo_rival
        return None


class Campeonato(db.Model):
    __tablename__ = "campeonato"
    __table_args__ = (
        db.CheckConstraint(
            "estado IN ('Borrador','Planificado','En curso','Finalizado','Cancelado')",
            name="ck_campeonato_estado",
        ),
        db.CheckConstraint(
            "formato IN ('Liga','Eliminación directa','Liga + eliminatorias','Manual')",
            name="ck_campeonato_formato",
        ),
        db.CheckConstraint("vueltas IN (1,2)", name="ck_campeonato_vueltas"),
        db.CheckConstraint("clasificados IN (2,4,8)", name="ck_campeonato_clasificados"),
    )
    id_campeonato = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    lugar = db.Column(db.String(150), nullable=True)
    id_lugar = db.Column(
        db.Integer, db.ForeignKey("lugar.id_lugar", ondelete="SET NULL"), nullable=True
    )
    estado = db.Column(db.String(20), default="Planificado")
    formato = db.Column(db.String(30), nullable=False, default="Liga")
    vueltas = db.Column(db.Integer, nullable=False, default=1)
    clasificados = db.Column(db.Integer, nullable=False, default=4)
    puntos_victoria = db.Column(db.Integer, nullable=False, default=3)
    puntos_empate = db.Column(db.Integer, nullable=False, default=1)
    puntos_derrota = db.Column(db.Integer, nullable=False, default=0)
    tercer_puesto = db.Column(db.Boolean, nullable=False, default=False)
    finalizado_en = db.Column(db.DateTime, nullable=True)
    motivo_cierre = db.Column(db.String(255), nullable=True)
    motivo_reapertura = db.Column(db.String(255), nullable=True)

    categorias = db.relationship("Categoria", secondary=campeonato_categoria, backref="campeonatos")
    equipos = db.relationship("Equipo", secondary=campeonato_equipo, backref="campeonatos")
    alumnos_habilitados = db.relationship(
        "AlumnoCampeonato", backref="campeonato", lazy=True, cascade="all, delete-orphan"
    )
    lugar_catalogo = db.relationship("Lugar")


class CampeonatoCategoriaConfig(db.Model):
    __tablename__ = "campeonato_categoria_config"
    __table_args__ = (
        db.UniqueConstraint(
            "id_campeonato", "id_categoria", name="uq_campeonato_categoria_config"
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    id_campeonato = db.Column(
        db.Integer, db.ForeignKey("campeonato.id_campeonato", ondelete="CASCADE"),
        nullable=False,
    )
    id_categoria = db.Column(
        db.Integer, db.ForeignKey("categoria.id_categoria", ondelete="RESTRICT"),
        nullable=False,
    )
    formato = db.Column(db.String(30), nullable=False, default="Liga")
    vueltas = db.Column(db.Integer, nullable=False, default=1)
    clasificados = db.Column(db.Integer, nullable=False, default=4)
    tercer_puesto = db.Column(db.Boolean, nullable=False, default=False)
    campeonato = db.relationship("Campeonato", backref=db.backref(
        "configuraciones_categoria", cascade="all, delete-orphan"
    ))
    categoria = db.relationship("Categoria")


class PodioCampeonato(db.Model):
    __tablename__ = "podio_campeonato"
    __table_args__ = (
        db.UniqueConstraint(
            "id_campeonato", "id_categoria", name="uq_podio_campeonato_categoria"
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    id_campeonato = db.Column(
        db.Integer, db.ForeignKey("campeonato.id_campeonato", ondelete="CASCADE"),
        nullable=False,
    )
    id_categoria = db.Column(
        db.Integer, db.ForeignKey("categoria.id_categoria", ondelete="RESTRICT"),
        nullable=False,
    )
    id_campeon = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo", ondelete="RESTRICT"))
    id_subcampeon = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo", ondelete="RESTRICT"))
    id_tercero = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo", ondelete="RESTRICT"))
    registrado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    campeonato = db.relationship("Campeonato", backref=db.backref(
        "podios", cascade="all, delete-orphan"
    ))
    categoria = db.relationship("Categoria")
    campeon = db.relationship("Equipo", foreign_keys=[id_campeon])
    subcampeon = db.relationship("Equipo", foreign_keys=[id_subcampeon])
    tercero = db.relationship("Equipo", foreign_keys=[id_tercero])


class AlumnoCampeonato(db.Model):
    """Habilitación de un jugador para un campeonato específico."""
    __tablename__ = "alumno_campeonato"
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno"), primary_key=True)
    id_campeonato = db.Column(db.Integer, db.ForeignKey("campeonato.id_campeonato"), primary_key=True)
    habilitado = db.Column(db.Boolean, default=True)
    archivado = db.Column(db.Boolean, nullable=False, default=False)
    archivado_en = db.Column(db.DateTime, nullable=True)


class Posicion(db.Model):
    """Tabla de posiciones por categoría dentro de un campeonato."""
    __tablename__ = "posicion"
    __table_args__ = (
        db.UniqueConstraint(
            "id_campeonato", "id_categoria", "id_equipo",
            name="uq_posicion_campeonato_categoria_equipo",
        ),
        db.CheckConstraint("pj >= 0 AND pg >= 0 AND pe >= 0 AND pp >= 0 AND gf >= 0 AND gc >= 0", name="ck_posicion_valores"),
    )
    id = db.Column(db.Integer, primary_key=True)
    id_campeonato = db.Column(db.Integer, db.ForeignKey("campeonato.id_campeonato"), nullable=False)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=False)
    id_equipo = db.Column(db.Integer, db.ForeignKey("equipo.id_equipo"), nullable=False)
    pj = db.Column(db.Integer, default=0)
    pg = db.Column(db.Integer, default=0)
    pe = db.Column(db.Integer, default=0)
    pp = db.Column(db.Integer, default=0)
    gf = db.Column(db.Integer, default=0)
    gc = db.Column(db.Integer, default=0)

    equipo = db.relationship("Equipo")
    categoria = db.relationship("Categoria")
    campeonato = db.relationship("Campeonato")

    @property
    def dg(self):
        return self.gf - self.gc

    @property
    def pts(self):
        if self.campeonato:
            return (
                self.pg * self.campeonato.puntos_victoria
                + self.pe * self.campeonato.puntos_empate
                + self.pp * self.campeonato.puntos_derrota
            )
        return self.pg * 3 + self.pe


class Convocatoria(db.Model):
    """Lista oficial de jugadores convocados a un partido o evento por categoría."""
    __tablename__ = "convocatoria"
    id_convocatoria = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria", ondelete="CASCADE"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=True)
    lugar = db.Column(db.String(150), nullable=True)
    rival = db.Column(db.String(150), nullable=True)
    indicaciones = db.Column(db.Text, nullable=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)

    categoria = db.relationship("Categoria")
    usuario = db.relationship("Usuario")
    detalles = db.relationship(
        "DetalleConvocatoria",
        back_populates="convocatoria",
        cascade="all, delete-orphan",
        order_by="DetalleConvocatoria.orden, DetalleConvocatoria.id_detalle",
    )

    @property
    def total_convocados(self):
        return len(self.detalles)

    @property
    def titulares(self):
        return [d for d in self.detalles if d.rol == "Titular"]

    @property
    def suplentes(self):
        return [d for d in self.detalles if d.rol != "Titular"]


class DetalleConvocatoria(db.Model):
    """Detalle de jugador convocado con rol, dorsal y notas."""
    __tablename__ = "detalle_convocatoria"
    __table_args__ = (
        db.UniqueConstraint("id_convocatoria", "id_alumno", name="uq_convocatoria_alumno"),
    )
    id_detalle = db.Column(db.Integer, primary_key=True)
    id_convocatoria = db.Column(
        db.Integer, db.ForeignKey("convocatoria.id_convocatoria", ondelete="CASCADE"), nullable=False
    )
    id_alumno = db.Column(
        db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="CASCADE"), nullable=False
    )
    rol = db.Column(db.String(30), nullable=False, default="Titular")
    dorsal = db.Column(db.Integer, nullable=True)
    posicion = db.Column(db.String(40), nullable=True)
    nota = db.Column(db.String(200), nullable=True)
    orden = db.Column(db.Integer, nullable=False, default=0)

    convocatoria = db.relationship("Convocatoria", back_populates="detalles")
    alumno = db.relationship("Alumno")

