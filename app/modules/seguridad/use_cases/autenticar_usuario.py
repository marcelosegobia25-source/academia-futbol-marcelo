from datetime import datetime, timezone
from app.extensions import db
from app.models import Usuario, Auditoria


def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AutenticarUsuarioUseCase:
    """Caso de uso: Autenticación segura de usuarios en el sistema."""

    def ejecutar(self, nombre_usuario, contrasena):
        usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()
        if not usuario:
            return None, "Usuario o contraseña incorrectos."

        if not usuario.activo:
            return None, "Esta cuenta ha sido desactivada por el administrador."

        if not usuario.verificar_contrasena(contrasena):
            return None, "Usuario o contraseña incorrectos."

        usuario.ultimo_acceso = ahora_utc()
        db.session.commit()

        return usuario, None
