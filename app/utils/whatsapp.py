import os
import json
import re
from config import INSTANCE_DIR

ARCHIVO_PLANTILLAS = os.path.join(INSTANCE_DIR, "whatsapp_plantillas.json")

PLANTILLAS_PREDETERMINADAS = {
    "prefijo_pais": "591",
    "deuda": (
        "Hola estimado(a) tutor(a) / familia de *{nombre}*:\n\n"
        "Le enviamos un cordial saludo de la *{academia}*.\n\n"
        "Nos comunicamos para recordarle amablemente que presenta una mensualidad pendiente de regularización:\n"
        "📋 *Alumno:* {nombre}\n"
        "⚽ *Categoría:* {categoria}\n"
        "⚠️ *Estado:* {estado_mensualidad} (Vencimiento: {vencimiento})\n"
        "💰 *Monto a regularizar:* {monto} {moneda}\n\n"
        "Le agradecemos coordinar la cancelación a la brevedad posible para mantener activa la cobertura y continuidad deportiva del alumno. "
        "Si ya realizó el pago, por favor remítanos el comprobante por este medio.\n\n"
        "¡Muchas gracias por su atención y compromiso!"
    ),
    "proximo_vencer": (
        "Hola estimado(a) tutor(a) / familia de *{nombre}*:\n\n"
        "Le enviamos un cordial saludo de la *{academia}*.\n\n"
        "Le recordamos de manera preventiva que la mensualidad del alumno *{nombre}* ({categoria}) vencerá próximamente el *{vencimiento}*.\n"
        "💰 *Monto:* {monto} {moneda}\n\n"
        "Agradecemos tomar las previsiones correspondientes para mantener su cobertura deportiva activa sin interrupciones.\n\n"
        "¡Muchas gracias y que tenga un excelente día!"
    ),
    "al_dia": (
        "Hola estimado(a) tutor(a) / familia de *{nombre}*:\n\n"
        "Desde la *{academia}* le agradecemos sinceramente por su pago y puntualidad.\n\n"
        "Confirmamos que el alumno *{nombre}* ({categoria}) se encuentra al día con sus cuotas deportivas, con cobertura vigente hasta el *{vencimiento}*.\n\n"
        "¡Agradecemos mucho su confianza y apoyo constante en la formación deportiva de su hijo(a)!"
    ),
    "citacion": (
        "⚽ *CITACIÓN DEPORTIVA - {academia}*\n\n"
        "Hola *{nombre}* y familia:\n"
        "Te recordamos la programación de tu próximo entrenamiento o partido:\n\n"
        "⚽ *Categoría:* {categoria}\n"
        "🕒 *Turno / Horario:* {turno}\n"
        "📍 *Lugar / Cancha:* [Cancha habitual]\n"
        "👕 *Indumentaria:* Camiseta oficial, medias, canilleras y tomatodo de hidratación.\n\n"
        "¡Contamos con tu puntualidad y compromiso para dar lo mejor en la cancha!"
    ),
    "comunicado": (
        "📢 *COMUNICADO OFICIAL - {academia}*\n\n"
        "Estimada familia del alumno *{nombre}*:\n\n"
        "Nos comunicamos de la dirección de la academia para compartirles el siguiente comunicado importante:\n\n"
        "[Escriba aquí los detalles del comunicado o actividad especial]\n\n"
        "Quedamos atentos a cualquier consulta. ¡Muchas gracias por su atención y colaboración!"
    ),
    "cumpleanos": (
        "🎉🎂 *¡MUY FELIZ CUMPLEAÑOS {nombre}!* 🎂🎉\n\n"
        "De parte de todo el equipo de profesores, compañeros y directiva de la *{academia}*, te deseamos un maravilloso cumpleaños lleno de alegría, bendiciones y mucho fútbol.\n\n"
        "¡Nos enorgullece tenerte en nuestra academia y te deseamos el mayor de los éxitos dentro y fuera de la cancha! ⚽👏"
    ),
    "personalizado": (
        "Hola estimado(a) tutor(a) / familia de *{nombre}*:\n\n"
        "Le saludamos de la *{academia}*.\n\n"
        "[Escriba aquí su mensaje]"
    ),
}


def obtener_plantillas_whatsapp():
    """Retorna el diccionario de plantillas de WhatsApp configuradas o las predeterminadas."""
    plantillas = dict(PLANTILLAS_PREDETERMINADAS)
    if os.path.exists(ARCHIVO_PLANTILLAS):
        try:
            with open(ARCHIVO_PLANTILLAS, "r", encoding="utf-8") as f:
                cargadas = json.load(f)
                if isinstance(cargadas, dict):
                    plantillas.update(cargadas)
        except Exception:
            pass
    return plantillas


def guardar_plantillas_whatsapp(nuevas_plantillas):
    """Guarda las plantillas personalizadas en archivo JSON en instance."""
    os.makedirs(os.path.dirname(ARCHIVO_PLANTILLAS), exist_ok=True)
    plantillas = dict(PLANTILLAS_PREDETERMINADAS)
    plantillas.update(nuevas_plantillas)
    with open(ARCHIVO_PLANTILLAS, "w", encoding="utf-8") as f:
        json.dump(plantillas, f, ensure_ascii=False, indent=2)
    return plantillas


def formatear_numero_whatsapp(telefono, prefijo="591"):
    """Limpia el teléfono y agrega el prefijo de país si tiene formato local."""
    if not telefono:
        return ""
    solo_digitos = re.sub(r"\D", "", str(telefono))
    if not solo_digitos:
        return ""
    # En Bolivia los números de celular tienen 8 dígitos (ej: 7xxxxxxx, 6xxxxxxx)
    prefijo_limpio = re.sub(r"\D", "", str(prefijo or "591"))
    if len(solo_digitos) == 8 and prefijo_limpio and not solo_digitos.startswith(prefijo_limpio):
        return f"{prefijo_limpio}{solo_digitos}"
    return solo_digitos

