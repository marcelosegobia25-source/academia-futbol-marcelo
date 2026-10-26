from decimal import Decimal
from app.extensions import db
from app.models import Configuracion, Auditoria
from app.utils.validacion import solo_numeros_opcional


class ActualizarConfiguracionUseCase:
    """Caso de uso: Actualización de datos institucionales y parámetros de la academia."""

    def ejecutar(self, datos, id_usuario=None):
        config = Configuracion.obtener()

        if "nombre_academia" in datos:
            config.nombre_academia = datos["nombre_academia"].strip()
        if "telefono" in datos:
            config.telefono = solo_numeros_opcional(datos["telefono"], "Teléfono", 50)
        if "direccion" in datos:
            config.direccion = datos["direccion"].strip() or None
        if "eslogan" in datos:
            config.eslogan = datos["eslogan"].strip() or None
        if "moneda" in datos:
            config.moneda = datos["moneda"].strip() or "BOB"
        if "monto_mensualidad" in datos:
            config.monto_mensualidad = Decimal(str(datos["monto_mensualidad"] or 0))
        if "dias_proximo_vencimiento" in datos:
            config.dias_proximo_vencimiento = int(datos["dias_proximo_vencimiento"] or 5)
        if "marcador_walkover" in datos:
            config.marcador_walkover = int(datos["marcador_walkover"] or 3)
        if "color_primario" in datos:
            config.color_primario = datos["color_primario"]
        if "color_secundario" in datos:
            config.color_secundario = datos["color_secundario"]
        if "color_acento" in datos:
            config.color_acento = datos["color_acento"]
        if "logo" in datos:
            config.logo = datos["logo"]

        auditoria = Auditoria(
            modulo="Configuración",
            accion="Actualizar configuración",
            entidad="Configuracion",
            id_entidad=config.id,
            detalle=f"Se actualizaron los parámetros institucionales de {config.nombre_academia}",
            id_usuario=id_usuario,
            valor_nuevo=config.nombre_academia,
        )
        db.session.add(auditoria)
        db.session.commit()

        return config
