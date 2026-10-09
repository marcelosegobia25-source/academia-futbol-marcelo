from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from app.extensions import db
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import event, text


def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


rol_permiso = db.Table(
    "rol_permiso",
    db.Column("id_rol", db.Integer, db.ForeignKey("rol.id_rol", ondelete="CASCADE"), primary_key=True),
    db.Column("id_permiso", db.Integer, db.ForeignKey("permiso.id_permiso", ondelete="CASCADE"), primary_key=True),
)


class Permiso(db.Model):
    __tablename__ = "permiso"
    id_permiso = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(60), nullable=False, unique=True)
    nombre = db.Column(db.String(120), nullable=False)


class Rol(db.Model):
    __tablename__ = "rol"
    id_rol = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60), nullable=False, unique=True)
    descripcion = db.Column(db.String(255), nullable=True)
    permisos = db.relationship("Permiso", secondary=rol_permiso, lazy="selectin")


class Usuario(db.Model):
    __tablename__ = "usuario"
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(40), nullable=False, unique=True)
    nombre_completo = db.Column(db.String(120), nullable=False)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    id_rol = db.Column(db.Integer, db.ForeignKey("rol.id_rol", ondelete="RESTRICT"), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    debe_cambiar_clave = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    rol = db.relationship("Rol", backref="usuarios")

    def establecer_contrasena(self, contrasena):
        self.contrasena_hash = generate_password_hash(contrasena)

    def verificar_contrasena(self, contrasena):
        return check_password_hash(self.contrasena_hash, contrasena)

    def tiene_permiso(self, codigo):
        return self.rol.nombre == "Administrador" or any(p.codigo == codigo for p in self.rol.permisos)


# --------------------------------------------------------------------------
# Tablas de asociación (relaciones N:M)
# --------------------------------------------------------------------------

alumno_equipo = db.Table(
    "alumno_equipo",
    db.Column("id_alumno", db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="CASCADE"), primary_key=True),
    db.Column("id_equipo", db.Integer, db.ForeignKey("equipo.id_equipo", ondelete="CASCADE"), primary_key=True),
)

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


# --------------------------------------------------------------------------
# Configuración general del sistema (singleton)
# --------------------------------------------------------------------------

class Configuracion(db.Model):
    __tablename__ = "configuracion"
    id = db.Column(db.Integer, primary_key=True)
    monto_mensualidad = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    nombre_academia = db.Column(db.String(150), nullable=False, default="Mi Academia Deportiva")
    telefono = db.Column(db.String(50), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    moneda = db.Column(db.String(10), nullable=False, default="BOB")
    dias_proximo_vencimiento = db.Column(db.Integer, nullable=False, default=5)
    marcador_walkover = db.Column(db.Integer, nullable=False, default=3)
    gestion_ficha = db.Column(db.Integer, nullable=False, default=lambda: date.today().year)
    eslogan = db.Column(db.String(180), nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    color_primario = db.Column(db.String(7), nullable=False, default="#2563eb")
    color_secundario = db.Column(db.String(7), nullable=False, default="#0f172a")
    color_acento = db.Column(db.String(7), nullable=False, default="#16a34a")
    contrasena_hash = db.Column(db.String(255), nullable=True)

    def establecer_contrasena(self, contrasena):
        self.contrasena_hash = generate_password_hash(contrasena)

    def verificar_contrasena(self, contrasena):
        return bool(
            self.contrasena_hash
            and check_password_hash(self.contrasena_hash, contrasena)
        )

    @staticmethod
    def obtener():
        config = Configuracion.query.first()
        if config is None:
            config = Configuracion(monto_mensualidad=0)
            db.session.add(config)
            db.session.commit()
        if not config.contrasena_hash:
            config.establecer_contrasena("00000")
            db.session.commit()
        if not config.gestion_ficha:
            config.gestion_ficha = date.today().year
            db.session.commit()
        return config


# --------------------------------------------------------------------------
# Canchas y lugares reutilizables
# --------------------------------------------------------------------------

TIPOS_LUGAR = ["Cancha", "Lugar"]


class Lugar(db.Model):
    __tablename__ = "lugar"
    id_lugar = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)
    tipo = db.Column(db.String(20), nullable=False, default="Cancha")
    direccion = db.Column(db.String(255), nullable=True)
    google_maps_url = db.Column(db.String(600), nullable=True)
    capacidad = db.Column(db.Integer, nullable=True)
    superficie = db.Column(db.String(80), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Lugar {self.nombre}>"


# --------------------------------------------------------------------------
# Categoría
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Equipo
# --------------------------------------------------------------------------

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

    alumnos = db.relationship("Alumno", secondary=alumno_equipo, back_populates="equipos")

    def __repr__(self):
        tipo = "Rival" if self.es_rival else "Equipo"
        return f"<{tipo} {self.nombre}>"


# --------------------------------------------------------------------------
# Alumno
# --------------------------------------------------------------------------

ESTADOS_ALUMNO = ["Activo", "Retirado"]
POSICIONES = ["DEL", "DEF", "MED", "POR"]
PIERNAS = ["Izquierda", "Derecha", "Ambas"]
SEXOS = ["M", "F"]
BECAS = ["Ninguna", "Media", "Completa"]
TURNOS = ["Mañana", "Tarde", "Noche"]


class Alumno(db.Model):
    __tablename__ = "alumno"
    __table_args__ = (
        db.Index(
            "uq_alumno_ci",
            "ci",
            unique=True,
            sqlite_where=db.text("ci IS NOT NULL AND trim(ci) <> ''"),
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
    categoria_manual = db.Column(db.Boolean, default=False)  # si True, no se recalcula automáticamente
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
    beca_fecha_fin = db.Column(db.Date, nullable=True)  # tiempo de beca definido por rendimiento

    # Fecha base de pago: se define en el primer pago y es modificable;
    # a partir de ella se calculan los vencimientos por continuidad.
    fecha_base_pago = db.Column(db.Date, nullable=True)
    # Inicio del ciclo vigente después de una reactivación. Los pagos
    # anteriores permanecen como historial y no determinan la cobertura actual.
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
        """Estado de la mensualidad según el último pago registrado."""
        # El historial financiero se conserva, pero un retirado ya no forma
        # parte de la cobranza y nunca debe presentarse como moroso.
        if self.estado == "Retirado":
            return "Retirado"
        ultimo = self.ultimo_pago
        if ultimo is None:
            return "Sin pagos"
        return ultimo.estado_cobertura

    @property
    def campeonatos_activos(self):
        """Lista de nombres de campeonatos en los que el alumno está habilitado."""
        return [ac.campeonato.nombre for ac in self.campeonatos_habilitados if ac.habilitado]

    @property
    def beca_vigente(self):
        if self.beca_fecha_fin and self.beca_fecha_fin < date.today():
            return "Ninguna"
        return self.beca or "Ninguna"

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


# --------------------------------------------------------------------------
# Pago de mensualidad
# --------------------------------------------------------------------------

MODOS_PAGO = ["Efectivo", "QR"]
ESTADOS_PAGO = ["Vigente", "Próximo a vencer", "Pagado"]
ESTADOS_MENSUALIDAD = ["Vigente", "Próximo a vencer", "Vencido", "Retirado"]


class Pago(db.Model):
    __tablename__ = "pago"
    __table_args__ = (
        db.Index("ix_pago_alumno_mes", "id_alumno", "mes_pagado"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR')", name="ck_pago_modo"),
        db.CheckConstraint("monto >= 0", name="ck_pago_monto"),
    )
    id_pago = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno"), nullable=False)
    es_beca = db.Column(db.Boolean, default=False)  # pago cubierto por beca (opcional)
    fecha_pago = db.Column(db.Date, nullable=False)
    hora_registro = db.Column(db.Time, default=lambda: datetime.now().time())
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    mes_pagado = db.Column(db.String(7), nullable=False)  # formato "YYYY-MM"
    modo_pago = db.Column(db.String(10), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    creado_en = db.Column(db.DateTime, default=ahora_utc)
    eliminado_en = db.Column(db.DateTime, nullable=True)
    numero_operacion = db.Column(db.String(80), nullable=True)

    @property
    def activo(self):
        return self.eliminado_en is None

    @property
    def estado(self):
        """Estado mostrado en el historial del pago.

        Una cuota que fue cancelada no se convierte en una deuda cuando
        termina su periodo: pasa a formar parte del historial como Pagado.
        """
        if not self.activo:
            return "Anulado"
        if date.today() > self.fecha_vencimiento:
            return "Pagado"
        return self.estado_cobertura

    @property
    def estado_cobertura(self):
        """Vigencia actual que este pago proporciona al alumno."""
        hoy = date.today()
        if hoy > self.fecha_vencimiento:
            return "Vencido"
        config = Configuracion.query.first()
        dias_aviso = config.dias_proximo_vencimiento if config else 5
        if (self.fecha_vencimiento - hoy).days <= dias_aviso:
            return "Próximo a vencer"
        return "Vigente"

    def __repr__(self):
        return f"<Pago {self.id_pago} alumno={self.id_alumno} mes={self.mes_pagado}>"


class Obligacion(db.Model):
    """Deuda o concepto cobrable independiente de los abonos que la cancelan."""
    __tablename__ = "obligacion"
    __table_args__ = (
        db.UniqueConstraint("id_alumno", "concepto", "periodo", name="uq_obligacion_alumno_concepto_periodo"),
        db.CheckConstraint("monto_original >= 0 AND descuento >= 0 AND recargo >= 0", name="ck_obligacion_importes"),
    )
    id_obligacion = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno", ondelete="RESTRICT"), nullable=False)
    concepto = db.Column(db.String(40), nullable=False, default="Mensualidad")
    periodo = db.Column(db.String(7), nullable=False)
    monto_original = db.Column(db.Numeric(10, 2), nullable=False)
    descuento = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    recargo = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    cubierto_beca = db.Column(db.Boolean, nullable=False, default=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    alumno = db.relationship("Alumno", backref=db.backref("obligaciones", lazy=True))
    aplicaciones = db.relationship("AplicacionPago", back_populates="obligacion", cascade="all, delete-orphan")

    @property
    def total(self):
        return max(Decimal("0.00"), Decimal(self.monto_original or 0) - Decimal(self.descuento or 0) + Decimal(self.recargo or 0))

    @property
    def pagado(self):
        return sum((Decimal(a.monto or 0) for a in self.aplicaciones if a.pago and a.pago.activo), Decimal("0.00"))

    @property
    def saldo(self):
        return max(Decimal("0.00"), self.total - self.pagado)

    @property
    def estado(self):
        if self.cubierto_beca:
            return "Cubierto por beca"
        if self.saldo <= 0:
            return "Pagada"
        if self.pagado > 0:
            return "Parcial"
        return "Pendiente"


class AplicacionPago(db.Model):
    __tablename__ = "aplicacion_pago"
    id_aplicacion = db.Column(db.Integer, primary_key=True)
    id_obligacion = db.Column(db.Integer, db.ForeignKey("obligacion.id_obligacion", ondelete="RESTRICT"), nullable=False)
    id_pago = db.Column(db.Integer, db.ForeignKey("pago.id_pago", ondelete="RESTRICT"), nullable=False, unique=True)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    obligacion = db.relationship("Obligacion", back_populates="aplicaciones")
    pago = db.relationship("Pago", backref=db.backref("aplicacion", uselist=False))


class Tarifa(db.Model):
    __tablename__ = "tarifa"
    id_tarifa = db.Column(db.Integer, primary_key=True)
    concepto = db.Column(db.String(40), nullable=False, default="Mensualidad")
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)


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


class AnulacionPago(db.Model):
    """Reversión formal e inmutable de un pago."""
    __tablename__ = "anulacion_pago"
    id_anulacion = db.Column(db.Integer, primary_key=True)
    id_pago = db.Column(
        db.Integer, db.ForeignKey("pago.id_pago", ondelete="RESTRICT"),
        nullable=False, unique=True,
    )
    motivo = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    id_pago_reemplazo = db.Column(
        db.Integer, db.ForeignKey("pago.id_pago", ondelete="SET NULL"), nullable=True
    )
    pago = db.relationship("Pago", foreign_keys=[id_pago], backref=db.backref("anulacion", uselist=False))
    pago_reemplazo = db.relationship("Pago", foreign_keys=[id_pago_reemplazo])


class CierreCaja(db.Model):
    __tablename__ = "cierre_caja"
    __table_args__ = (
        db.CheckConstraint("efectivo_sistema >= 0 AND qr_sistema >= 0", name="ck_cierre_sistema"),
        db.CheckConstraint("efectivo_contado >= 0 AND qr_confirmado >= 0", name="ck_cierre_contado"),
    )
    id_cierre = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, unique=True)
    efectivo_sistema = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    qr_sistema = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    efectivo_contado = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    qr_confirmado = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    diferencia = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    observacion = db.Column(db.String(255), nullable=True)
    cerrado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    reabierto_en = db.Column(db.DateTime, nullable=True)
    motivo_reapertura = db.Column(db.String(255), nullable=True)


class SesionCaja(db.Model):
    __tablename__ = "sesion_caja"
    __table_args__ = (
        db.CheckConstraint("estado IN ('Abierta','Cerrada','Reabierta')", name="ck_sesion_caja_estado"),
        db.CheckConstraint("saldo_inicial >= 0", name="ck_sesion_caja_saldo_inicial"),
    )
    id_sesion = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"), nullable=False)
    abierta_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    saldo_inicial = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    cerrada_en = db.Column(db.DateTime, nullable=True)
    efectivo_esperado = db.Column(db.Numeric(12, 2), nullable=True)
    efectivo_contado = db.Column(db.Numeric(12, 2), nullable=True)
    diferencia = db.Column(db.Numeric(12, 2), nullable=True)
    estado = db.Column(db.String(12), nullable=False, default="Abierta")
    observacion = db.Column(db.String(255), nullable=True)
    motivo_reapertura = db.Column(db.String(255), nullable=True)
    id_cierre_legacy = db.Column(db.Integer, db.ForeignKey("cierre_caja.id_cierre", ondelete="SET NULL"), nullable=True, unique=True)
    usuario = db.relationship("Usuario")
    movimientos_caja = db.relationship("MovimientoCaja", back_populates="sesion")

    @property
    def ingresos_efectivo(self):
        return sum((Decimal(m.monto) for m in self.movimientos_caja if m.activo and m.tipo == "Ingreso" and m.modo_pago == "Efectivo"), Decimal("0"))

    @property
    def egresos_efectivo(self):
        return sum((Decimal(m.monto) for m in self.movimientos_caja if m.activo and m.tipo == "Egreso" and m.modo_pago == "Efectivo"), Decimal("0"))

    @property
    def esperado_actual(self):
        return Decimal(self.saldo_inicial or 0) + self.ingresos_efectivo - self.egresos_efectivo


class MovimientoCaja(db.Model):
    __tablename__ = "movimiento_caja"
    id_movimiento_caja = db.Column(db.Integer, primary_key=True)
    id_sesion = db.Column(db.Integer, db.ForeignKey("sesion_caja.id_sesion", ondelete="RESTRICT"), nullable=False)
    id_movimiento_contable = db.Column(db.Integer, db.ForeignKey("movimiento_contable.id_movimiento", ondelete="RESTRICT"), nullable=False, unique=True)
    tipo = db.Column(db.String(10), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    modo_pago = db.Column(db.String(20), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    sesion = db.relationship("SesionCaja", back_populates="movimientos_caja")
    movimiento_contable = db.relationship("MovimientoContable")

    @property
    def activo(self):
        return bool(self.movimiento_contable and self.movimiento_contable.activo)


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


class Auditoria(db.Model):
    """Bitácora local de operaciones sensibles; no contiene contraseñas."""
    __tablename__ = "auditoria"
    id_auditoria = db.Column(db.Integer, primary_key=True)
    modulo = db.Column(db.String(40), nullable=False)
    accion = db.Column(db.String(60), nullable=False)
    entidad = db.Column(db.String(40), nullable=True)
    id_entidad = db.Column(db.Integer, nullable=True)
    detalle = db.Column(db.Text, nullable=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True)
    valor_anterior = db.Column(db.Text, nullable=True)
    valor_nuevo = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    usuario = db.relationship("Usuario")


@event.listens_for(Auditoria, "before_insert")
def _asignar_actor_auditoria(mapper, connection, objetivo):
    if objetivo.id_usuario is not None:
        return
    try:
        from flask import has_request_context, session
        if has_request_context():
            objetivo.id_usuario = session.get("id_usuario")
    except RuntimeError:
        pass
    if objetivo.valor_anterior is None and objetivo.valor_nuevo is None and objetivo.detalle:
        if any(palabra in (objetivo.accion or "").lower() for palabra in ("eliminar", "anular", "retirar", "desactivar")):
            objetivo.valor_anterior = objetivo.detalle
        else:
            objetivo.valor_nuevo = objetivo.detalle


# --------------------------------------------------------------------------
# Contabilidad, inventario y ventas
# --------------------------------------------------------------------------

MODOS_MOVIMIENTO = ["Efectivo", "QR", "Transferencia", "Otro"]


class Proveedor(db.Model):
    __tablename__ = "proveedor"
    __table_args__ = (db.CheckConstraint("length(trim(nombre)) > 0", name="ck_proveedor_nombre"),)
    id_proveedor = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)
    tipo_persona = db.Column(db.String(10), nullable=False, default="Persona")
    documento = db.Column(db.String(40), nullable=True)
    correo = db.Column(db.String(120), nullable=True)
    contacto = db.Column(db.String(120), nullable=True)
    telefono = db.Column(db.String(50), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    observacion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class CategoriaContable(db.Model):
    __tablename__ = "categoria_contable"
    __table_args__ = (db.CheckConstraint("tipo IN ('Ingreso','Egreso','Ambos')", name="ck_categoria_contable_tipo"),)
    id_categoria_contable = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False, unique=True)
    tipo = db.Column(db.String(10), nullable=False, default="Ambos")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)


class MovimientoContable(db.Model):
    __tablename__ = "movimiento_contable"
    __table_args__ = (
        db.CheckConstraint("tipo IN ('Ingreso','Egreso')", name="ck_movimiento_tipo"),
        db.CheckConstraint("monto >= 0", name="ck_movimiento_monto"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR','Transferencia','Otro')", name="ck_movimiento_modo"),
        db.CheckConstraint("(origen_tipo IS NULL) = (origen_id IS NULL)", name="ck_movimiento_origen_completo"),
        db.UniqueConstraint("origen_tipo", "origen_id", name="uq_movimiento_origen"),
    )
    id_movimiento = db.Column(db.Integer, primary_key=True)
    id_sesion_caja = db.Column(db.Integer, db.ForeignKey("sesion_caja.id_sesion", ondelete="SET NULL"), nullable=True)
    tipo = db.Column(db.String(10), nullable=False)
    categoria = db.Column(db.String(80), nullable=False)
    id_categoria_contable = db.Column(db.Integer, db.ForeignKey("categoria_contable.id_categoria_contable", ondelete="RESTRICT"), nullable=True)
    concepto = db.Column(db.String(180), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    modo_pago = db.Column(db.String(20), nullable=False, default="Efectivo")
    numero_operacion = db.Column(db.String(100), nullable=True)
    id_proveedor = db.Column(db.Integer, db.ForeignKey("proveedor.id_proveedor"), nullable=True)
    comprobante = db.Column(db.String(255), nullable=True)
    observacion = db.Column(db.String(255), nullable=True)
    origen_tipo = db.Column(db.String(30), nullable=True)
    origen_id = db.Column(db.Integer, nullable=True)
    anulado_en = db.Column(db.DateTime, nullable=True)
    motivo_anulacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    proveedor = db.relationship("Proveedor")
    sesion_caja = db.relationship("SesionCaja")
    categoria_rel = db.relationship("CategoriaContable")

    @property
    def activo(self):
        return self.anulado_en is None


@event.listens_for(MovimientoContable, "before_insert")
def _vincular_sesion_caja(mapper, connection, objetivo):
    if objetivo.id_sesion_caja is not None:
        return
    try:
        from flask import has_request_context, session
        id_usuario = session.get("id_usuario") if has_request_context() else None
    except RuntimeError:
        id_usuario = None
    if id_usuario:
        objetivo.id_sesion_caja = connection.execute(text(
            "SELECT id_sesion FROM sesion_caja WHERE id_usuario=:u AND estado IN ('Abierta','Reabierta') ORDER BY abierta_en DESC LIMIT 1"
        ), {"u": id_usuario}).scalar()


@event.listens_for(MovimientoContable, "after_insert")
def _crear_movimiento_caja(mapper, connection, objetivo):
    if objetivo.id_sesion_caja:
        connection.execute(text("""INSERT INTO movimiento_caja
            (id_sesion,id_movimiento_contable,tipo,monto,modo_pago,creado_en)
            VALUES (:s,:m,:t,:n,:p,:c)"""), {
            "s": objetivo.id_sesion_caja, "m": objetivo.id_movimiento,
            "t": objetivo.tipo, "n": float(objetivo.monto), "p": objetivo.modo_pago,
            "c": objetivo.creado_en or ahora_utc(),
        })


class Producto(db.Model):
    __tablename__ = "producto"
    __table_args__ = (
        db.CheckConstraint("length(trim(codigo)) > 0", name="ck_producto_codigo"),
        db.CheckConstraint("length(trim(nombre)) > 0", name="ck_producto_nombre"),
    )
    id_producto = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(40), nullable=False, unique=True)
    nombre = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(80), nullable=False, default="Uniformes")
    descripcion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)


class ProductoVariante(db.Model):
    __tablename__ = "producto_variante"
    __table_args__ = (
        db.UniqueConstraint("id_producto", "talla", "color", name="uq_producto_variante"),
        db.CheckConstraint("stock >= 0", name="ck_variante_stock"),
        db.CheckConstraint("precio_compra >= 0 AND precio_venta >= 0", name="ck_variante_precios"),
        db.CheckConstraint("stock_minimo >= 0", name="ck_variante_stock_minimo"),
    )
    id_variante = db.Column(db.Integer, primary_key=True)
    id_producto = db.Column(db.Integer, db.ForeignKey("producto.id_producto", ondelete="CASCADE"), nullable=False)
    talla = db.Column(db.String(30), nullable=False, default="Única")
    color = db.Column(db.String(50), nullable=False, default="Estándar")
    precio_compra = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    precio_venta = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo = db.Column(db.Integer, nullable=False, default=0)
    producto = db.relationship("Producto", backref=db.backref("variantes", cascade="all, delete-orphan"))

    @property
    def nombre_completo(self):
        return f"{self.producto.nombre} - {self.talla} - {self.color}"


class MovimientoInventario(db.Model):
    __tablename__ = "movimiento_inventario"
    __table_args__ = (
        db.CheckConstraint("cantidad <> 0", name="ck_inventario_cantidad"),
        db.CheckConstraint("stock_anterior >= 0 AND stock_nuevo >= 0", name="ck_inventario_stock"),
        db.CheckConstraint("stock_nuevo = stock_anterior + cantidad", name="ck_inventario_balance"),
    )
    id_movimiento = db.Column(db.Integer, primary_key=True)
    id_variante = db.Column(db.Integer, db.ForeignKey("producto_variante.id_variante"), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    stock_anterior = db.Column(db.Integer, nullable=False)
    stock_nuevo = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(255), nullable=True)
    origen_tipo = db.Column(db.String(30), nullable=True)
    origen_id = db.Column(db.Integer, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    variante = db.relationship("ProductoVariante")


class ConteoInventario(db.Model):
    __tablename__ = "conteo_inventario"
    id_conteo = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    estado = db.Column(db.String(12), nullable=False, default="Pendiente")
    observacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)


class DetalleConteoInventario(db.Model):
    __tablename__ = "detalle_conteo_inventario"
    __table_args__ = (db.UniqueConstraint("id_conteo", "id_variante", name="uq_conteo_variante"),)
    id_detalle_conteo = db.Column(db.Integer, primary_key=True)
    id_conteo = db.Column(db.Integer, db.ForeignKey("conteo_inventario.id_conteo", ondelete="CASCADE"), nullable=False)
    id_variante = db.Column(db.Integer, db.ForeignKey("producto_variante.id_variante", ondelete="RESTRICT"), nullable=False)
    stock_sistema = db.Column(db.Integer, nullable=False)
    stock_contado = db.Column(db.Integer, nullable=False)
    conteo = db.relationship("ConteoInventario", backref=db.backref("detalles", cascade="all, delete-orphan"))
    variante = db.relationship("ProductoVariante")


class Compra(db.Model):
    __tablename__ = "compra"
    __table_args__ = (
        db.CheckConstraint("total >= 0", name="ck_compra_total"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR','Transferencia','Otro')", name="ck_compra_modo"),
    )
    id_compra = db.Column(db.Integer, primary_key=True)
    id_proveedor = db.Column(db.Integer, db.ForeignKey("proveedor.id_proveedor", ondelete="RESTRICT"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    numero_factura = db.Column(db.String(80), nullable=True)
    modo_pago = db.Column(db.String(20), nullable=False, default="Efectivo")
    total = db.Column(db.Numeric(12, 2), nullable=False)
    observacion = db.Column(db.String(255), nullable=True)
    anulado_en = db.Column(db.DateTime, nullable=True)
    motivo_anulacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    proveedor = db.relationship("Proveedor", backref=db.backref("compras", lazy=True))

    @property
    def activo(self):
        return self.anulado_en is None


class DetalleCompra(db.Model):
    __tablename__ = "detalle_compra"
    __table_args__ = (
        db.CheckConstraint("cantidad > 0", name="ck_detalle_compra_cantidad"),
        db.CheckConstraint("costo_unitario >= 0 AND subtotal >= 0", name="ck_detalle_compra_montos"),
        db.CheckConstraint("abs(subtotal-(costo_unitario*cantidad)) < 0.01", name="ck_detalle_compra_subtotal"),
    )
    id_detalle_compra = db.Column(db.Integer, primary_key=True)
    id_compra = db.Column(db.Integer, db.ForeignKey("compra.id_compra", ondelete="RESTRICT"), nullable=False)
    id_variante = db.Column(db.Integer, db.ForeignKey("producto_variante.id_variante", ondelete="RESTRICT"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    costo_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    compra = db.relationship("Compra", backref=db.backref("detalles", cascade="all, delete-orphan"))
    variante = db.relationship("ProductoVariante")


class Venta(db.Model):
    __tablename__ = "venta"
    __table_args__ = (
        db.CheckConstraint("subtotal >= 0 AND descuento >= 0 AND total >= 0", name="ck_venta_montos"),
        db.CheckConstraint("descuento <= subtotal", name="ck_venta_descuento"),
        db.CheckConstraint("abs(total - (subtotal - descuento)) < 0.01", name="ck_venta_total"),
        db.CheckConstraint("id_alumno IS NOT NULL OR length(trim(COALESCE(cliente_externo,''))) > 0", name="ck_venta_cliente"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR','Transferencia','Otro')", name="ck_venta_modo"),
    )
    id_venta = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey("alumno.id_alumno"), nullable=True)
    cliente_externo = db.Column(db.String(150), nullable=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    modo_pago = db.Column(db.String(20), nullable=False, default="Efectivo")
    numero_operacion = db.Column(db.String(100), nullable=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    descuento = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    observacion = db.Column(db.String(255), nullable=True)
    anulado_en = db.Column(db.DateTime, nullable=True)
    motivo_anulacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    alumno = db.relationship("Alumno", backref=db.backref("ventas", order_by="desc(Venta.fecha)"))

    @property
    def activo(self):
        return self.anulado_en is None


class DetalleVenta(db.Model):
    __tablename__ = "detalle_venta"
    __table_args__ = (
        db.CheckConstraint("cantidad > 0", name="ck_detalle_cantidad"),
        db.CheckConstraint("precio_unitario >= 0 AND subtotal >= 0", name="ck_detalle_montos"),
        db.CheckConstraint("abs(subtotal - (precio_unitario * cantidad)) < 0.01", name="ck_detalle_subtotal"),
    )
    id_detalle = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey("venta.id_venta", ondelete="CASCADE"), nullable=False)
    id_variante = db.Column(db.Integer, db.ForeignKey("producto_variante.id_variante"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    venta = db.relationship("Venta", backref=db.backref("detalles", cascade="all, delete-orphan"))
    variante = db.relationship("ProductoVariante")


class DevolucionVenta(db.Model):
    __tablename__ = "devolucion_venta"
    id_devolucion = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey("venta.id_venta", ondelete="RESTRICT"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    tipo = db.Column(db.String(12), nullable=False, default="Devolución")
    total_credito = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    motivo = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    venta = db.relationship("Venta", backref="devoluciones")


class DetalleDevolucionVenta(db.Model):
    __tablename__ = "detalle_devolucion_venta"
    id_detalle_devolucion = db.Column(db.Integer, primary_key=True)
    id_devolucion = db.Column(db.Integer, db.ForeignKey("devolucion_venta.id_devolucion", ondelete="CASCADE"), nullable=False)
    id_detalle_venta = db.Column(db.Integer, db.ForeignKey("detalle_venta.id_detalle", ondelete="RESTRICT"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    devolucion = db.relationship("DevolucionVenta", backref=db.backref("detalles", cascade="all, delete-orphan"))
    detalle_venta = db.relationship("DetalleVenta")


class PagoProgramado(db.Model):
    """Obligación recurrente que genera cuotas, no egresos anticipados."""
    __tablename__ = "pago_programado"
    __table_args__ = (
        db.CheckConstraint("monto > 0", name="ck_programado_monto"),
        db.CheckConstraint("frecuencia IN ('Dias','Mensual')", name="ck_programado_frecuencia"),
        db.CheckConstraint("intervalo_dias IS NULL OR intervalo_dias > 0", name="ck_programado_intervalo"),
        db.CheckConstraint("dia_mes IS NULL OR dia_mes BETWEEN 1 AND 31", name="ck_programado_dia_mes"),
        db.CheckConstraint("fecha_fin IS NULL OR fecha_fin >= fecha_inicio", name="ck_programado_fechas"),
        db.CheckConstraint("modo_pago IN ('Efectivo','QR','Transferencia','Otro')", name="ck_programado_modo"),
    )
    id_programado = db.Column(db.Integer, primary_key=True)
    concepto = db.Column(db.String(180), nullable=False)
    categoria = db.Column(db.String(80), nullable=False)
    id_categoria_contable = db.Column(db.Integer, db.ForeignKey("categoria_contable.id_categoria_contable", ondelete="RESTRICT"), nullable=True)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    id_proveedor = db.Column(db.Integer, db.ForeignKey("proveedor.id_proveedor"), nullable=True)
    modo_pago = db.Column(db.String(20), nullable=False, default="Efectivo")
    frecuencia = db.Column(db.String(10), nullable=False)
    intervalo_dias = db.Column(db.Integer, nullable=True)
    dia_mes = db.Column(db.Integer, nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    proxima_fecha = db.Column(db.Date, nullable=True)
    observacion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    proveedor = db.relationship("Proveedor")
    categoria_rel = db.relationship("CategoriaContable")


class CuotaProgramada(db.Model):
    __tablename__ = "cuota_programada"
    __table_args__ = (
        db.UniqueConstraint("id_programado", "fecha_vencimiento", name="uq_cuota_programada_fecha"),
        db.CheckConstraint("monto > 0", name="ck_cuota_programada_monto"),
        db.CheckConstraint("estado IN ('Pendiente','Pagado','Omitido')", name="ck_cuota_programada_estado"),
    )
    id_cuota = db.Column(db.Integer, primary_key=True)
    id_programado = db.Column(db.Integer, db.ForeignKey("pago_programado.id_programado", ondelete="CASCADE"), nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    estado = db.Column(db.String(12), nullable=False, default="Pendiente")
    fecha_pago = db.Column(db.Date, nullable=True)
    id_movimiento = db.Column(db.Integer, db.ForeignKey("movimiento_contable.id_movimiento", ondelete="SET NULL"), nullable=True, unique=True)
    motivo_omision = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    programado = db.relationship("PagoProgramado", backref=db.backref("cuotas", order_by="CuotaProgramada.fecha_vencimiento.desc()", cascade="all, delete-orphan"))
    movimiento = db.relationship("MovimientoContable")


# --------------------------------------------------------------------------
# Partidos
# --------------------------------------------------------------------------

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
    resultado = db.Column(db.String(30), nullable=True)  # ej "3-1", vacío si aún no se jugó
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
    id_partido_origen_local = db.Column(db.Integer, db.ForeignKey("partido.id_partido"), nullable=True)
    id_partido_origen_visita = db.Column(db.Integer, db.ForeignKey("partido.id_partido"), nullable=True)

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


# --------------------------------------------------------------------------
# Agenda (eventos propios + partidos programados)
# --------------------------------------------------------------------------

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
    tipo = db.Column(db.String(20), default="Evento")  # Evento | Partido | Entrenamiento
    id_partido = db.Column(db.Integer, db.ForeignKey("partido.id_partido"), nullable=True)

    categoria = db.relationship("Categoria")
    equipo = db.relationship("Equipo")
    partido = db.relationship("Partido")
    lugar_catalogo = db.relationship("Lugar")


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
    dia_semana = db.Column(db.Integer, nullable=False)  # 0=lunes ... 6=domingo
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
        """Turno operativo derivado de la hora de inicio."""
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


class SesionEntrenamiento(db.Model):
    __tablename__ = "sesion_entrenamiento"
    __table_args__ = (db.UniqueConstraint("id_entrenamiento", "fecha", name="uq_sesion_entrenamiento_fecha"),)
    id_sesion_entrenamiento = db.Column(db.Integer, primary_key=True)
    id_entrenamiento = db.Column(db.Integer, db.ForeignKey("entrenamiento.id_entrenamiento", ondelete="RESTRICT"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(12), nullable=False, default="Programada")
    observacion = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    entrenamiento = db.relationship("Entrenamiento", backref=db.backref("sesiones", order_by="desc(SesionEntrenamiento.fecha)"))


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


# --------------------------------------------------------------------------
# Campeonato
# --------------------------------------------------------------------------

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
    estado = db.Column(db.String(20), default="Planificado")  # Planificado, En curso, Finalizado
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
