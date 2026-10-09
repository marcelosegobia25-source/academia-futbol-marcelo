from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import (
    Campeonato, Entrenamiento, EventoAgenda, Lugar, Partido, TIPOS_LUGAR, Auditoria,
)
from app.utils.validacion import ErrorValidacion, opcion, texto_opcional, texto_requerido, entero


bp = Blueprint("lugares", __name__, url_prefix="/lugares")


def _enlace_google_maps(valor):
    enlace = texto_opcional(valor, "Enlace de Google Maps", 600)
    if not enlace:
        return None
    partes = urlparse(enlace)
    host = (partes.hostname or "").lower()
    es_google_maps = (
        partes.scheme in {"http", "https"}
        and (
            host == "maps.app.goo.gl"
            or (host == "goo.gl" and partes.path.startswith("/maps"))
            or ("google." in host and ("/maps" in partes.path or host.startswith("maps.")))
        )
    )
    if not es_google_maps:
        raise ErrorValidacion(
            "Ingrese un enlace válido de Google Maps, por ejemplo https://maps.app.goo.gl/..."
        )
    return enlace


@bp.route("/")
def listar():
    lugares = Lugar.query.order_by(Lugar.activo.desc(), Lugar.tipo, Lugar.nombre).all()
    return render_template("lugares/listar.html", lugares=lugares)


def _datos_formulario(id_lugar=None):
    nombre = texto_requerido(request.form.get("nombre"), "Nombre", 150)
    repetido = Lugar.query.filter(db.func.lower(Lugar.nombre) == nombre.lower())
    if id_lugar:
        repetido = repetido.filter(Lugar.id_lugar != id_lugar)
    if repetido.first():
        raise ErrorValidacion("Ya existe una cancha o lugar con ese nombre.")
    return {
        "nombre": nombre,
        "tipo": opcion(request.form.get("tipo"), TIPOS_LUGAR, "Tipo"),
        "direccion": texto_opcional(request.form.get("direccion"), "Dirección", 255),
        "google_maps_url": _enlace_google_maps(request.form.get("google_maps_url")),
        "capacidad": entero(request.form.get("capacidad"), "Capacidad", 1, 100000),
        "superficie": texto_opcional(request.form.get("superficie"), "Superficie", 80),
        "activo": request.form.get("activo") == "1",
    }


@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    if request.method == "POST":
        try:
            datos = _datos_formulario()
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "lugares/form.html", lugar=None, tipos=TIPOS_LUGAR
            )
        lugar = Lugar(**datos)
        db.session.add(lugar)
        db.session.flush()
        db.session.add(Auditoria(
            modulo="Lugares", accion="Crear", entidad="Lugar",
            id_entidad=lugar.id_lugar, detalle=lugar.nombre,
        ))
        db.session.commit()
        flash(f"{lugar.tipo} '{lugar.nombre}' registrado correctamente.", "success")
        return redirect(url_for("lugares.listar"))
    return render_template("lugares/form.html", lugar=None, tipos=TIPOS_LUGAR)


@bp.route("/<int:id_lugar>/editar", methods=["GET", "POST"])
def editar(id_lugar):
    lugar = Lugar.query.get_or_404(id_lugar)
    if request.method == "POST":
        nombre_anterior = lugar.nombre
        try:
            datos = _datos_formulario(id_lugar)
        except ErrorValidacion as error:
            flash(str(error), "danger")
            return render_template(
                "lugares/form.html", lugar=lugar, tipos=TIPOS_LUGAR
            )
        for campo, valor in datos.items():
            setattr(lugar, campo, valor)
        # El nombre guardado en partidos, agenda, entrenamientos y campeonatos
        # es un snapshot histórico. Renombrar el catálogo no reescribe el pasado.
        db.session.add(Auditoria(
            modulo="Lugares", accion="Editar", entidad="Lugar",
            id_entidad=lugar.id_lugar, detalle=f"{nombre_anterior} -> {lugar.nombre}",
        ))
        db.session.commit()
        flash("Cancha o lugar actualizado.", "success")
        return redirect(url_for("lugares.listar"))
    return render_template("lugares/form.html", lugar=lugar, tipos=TIPOS_LUGAR)


@bp.route("/<int:id_lugar>/eliminar", methods=["POST"])
def eliminar(id_lugar):
    lugar = Lugar.query.get_or_404(id_lugar)
    nombre = lugar.nombre
    usado = (
        Partido.query.filter(db.func.lower(Partido.cancha) == nombre.lower()).first()
        or Campeonato.query.filter(db.func.lower(Campeonato.lugar) == nombre.lower()).first()
        or EventoAgenda.query.filter(db.func.lower(EventoAgenda.lugar) == nombre.lower()).first()
        or Entrenamiento.query.filter(db.func.lower(Entrenamiento.lugar) == nombre.lower()).first()
    )
    if usado:
        flash(
            "No se puede eliminar porque está utilizado. Puede desactivarlo al editar.",
            "danger",
        )
        return redirect(url_for("lugares.listar"))
    db.session.add(Auditoria(
        modulo="Lugares", accion="Eliminar", entidad="Lugar",
        id_entidad=id_lugar, detalle=nombre,
    ))
    db.session.delete(lugar)
    db.session.commit()
    flash("Cancha o lugar eliminado.", "success")
    return redirect(url_for("lugares.listar"))
