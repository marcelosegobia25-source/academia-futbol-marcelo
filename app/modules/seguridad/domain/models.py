from datetime import datetime, timezone
from app.extensions import db
from werkzeug.security import check_password_hash, generate_password_hash


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

    def __repr__(self):
        return f"<Permiso {self.codigo}>"


class Rol(db.Model):
    __tablename__ = "rol"
    id_rol = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60), nullable=False, unique=True)
    descripcion = db.Column(db.String(255), nullable=True)
    permisos = db.relationship("Permiso", secondary=rol_permiso, lazy="selectin")

    def __repr__(self):
        return f"<Rol {self.nombre}>"


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
        if not self.rol:
            return False
        if self.rol.nombre == "Administrador":
            return True
        codigos_asignados = {p.codigo for p in self.rol.permisos}
        if codigo in codigos_asignados:
            return True
        # Fallbacks de retrocompatibilidad para permisos granulares
        if codigo == "eliminar_alumnos" and "gestionar_alumnos" in codigos_asignados:
            return True
        if codigo in ("gestionar_equipos", "gestionar_lugares") and ("gestionar_deportivo" in codigos_asignados or "administrar" in codigos_asignados):
            return True
        if codigo == "gestionar_compras" and "gestionar_inventario" in codigos_asignados:
            return True
        return False

    def __repr__(self):
        return f"<Usuario {self.nombre_usuario}>"
