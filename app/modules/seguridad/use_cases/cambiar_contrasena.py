import re
from app.extensions import db
from app.models import Usuario, Auditoria


class CambiarContrasenaUseCase:
    """Caso de uso: Cambio de contraseña o PIN numérico de usuario."""

    def ejecutar(self, id_usuario, clave_actual, clave_nueva, id_solicitante=None):
        usuario = Usuario.query.get_or_404(id_usuario)

        # Si el usuario cambia su propia contraseña, exigir la clave actual
        if clave_actual is not None and not usuario.verificar_contrasena(clave_actual):
            return False, "La contraseña actual es incorrecta."

        if not re.match(r"^\d{5}$", clave_nueva):
            return False, "La nueva contraseña debe contener exactamente 5 números."

        usuario.establecer_contrasena(clave_nueva)
        usuario.debe_cambiar_clave = False

        auditoria = Auditoria(
            modulo="Seguridad",
            accion="Cambiar contraseña",
            entidad="Usuario",
            id_entidad=usuario.id_usuario,
            detalle=f"Cambio de clave de usuario: {usuario.nombre_usuario}",
            id_usuario=id_solicitante or usuario.id_usuario,
        )
        db.session.add(auditoria)
        db.session.commit()

        return True, "Contraseña actualizada exitosamente."
