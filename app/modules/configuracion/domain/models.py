from datetime import date, datetime, timezone
from sqlalchemy.orm import validates
from app.extensions import db
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import event
from app.utils.validacion import solo_numeros_opcional



def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


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

    @validates("telefono")
    def _validar_telefono(self, key, valor):
        return solo_numeros_opcional(valor, "Teléfono", 50)

    def establecer_contrasena(self, contrasena):
        self.contrasena_hash = generate_password_hash(contrasena)

    def verificar_contrasena(self, contrasena):
        return bool(
            self.contrasena_hash
            and check_password_hash(self.contrasena_hash, contrasena)
        )

    @staticmethod
    def obtener():
        try:
            from flask import g, has_app_context
            if has_app_context() and hasattr(g, "_configuracion_cache"):
                return g._configuracion_cache
        except ImportError:
            has_app_context = lambda: False

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

        try:
            if has_app_context():
                g._configuracion_cache = config
        except Exception:
            pass
        return config


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
    ip = db.Column(db.String(45), nullable=True, index=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    usuario = db.relationship("Usuario")


def obtener_ip_cliente(req=None):
    """Extrae de manera segura la IP del cliente considerando proxies y Cloudflare."""
    try:
        if req is None:
            from flask import has_request_context, request as flask_req
            if not has_request_context():
                return None
            req = flask_req
        ip = (
            req.headers.get("CF-Connecting-IP")
            or req.headers.get("X-Forwarded-For")
            or req.remote_addr
        )
        if ip:
            ip = ip.split(",")[0].strip()
            return ip[:45]
    except Exception:
        pass
    return None


@event.listens_for(Auditoria, "before_insert")
def _asignar_actor_auditoria(mapper, connection, objetivo):
    try:
        from flask import has_request_context, session
        if has_request_context():
            if objetivo.id_usuario is None:
                objetivo.id_usuario = session.get("id_usuario")
            if not objetivo.ip:
                objetivo.ip = obtener_ip_cliente()
    except RuntimeError:
        pass
    if objetivo.valor_anterior is None and objetivo.valor_nuevo is None and objetivo.detalle:
        if any(palabra in (objetivo.accion or "").lower() for palabra in ("eliminar", "anular", "retirar", "desactivar")):
            objetivo.valor_anterior = objetivo.detalle
        else:
            objetivo.valor_nuevo = objetivo.detalle
