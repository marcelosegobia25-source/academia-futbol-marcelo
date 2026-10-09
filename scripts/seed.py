"""Carga datos de demostracion para probar filtros, reportes y calendario.

Uso desde la raiz del proyecto:
    python scripts/seed.py --reset

Sin --reset, la carga se detiene si ya existen alumnos o campeonatos.
"""
import argparse
import sys
from datetime import date, time
from pathlib import Path

from dateutil.relativedelta import relativedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Alumno, AlumnoCampeonato, Campeonato, Categoria, Configuracion,
    Entrenamiento, Equipo, EventoAgenda, Pago, Partido, Posicion,
    alumno_equipo, campeonato_categoria, campeonato_equipo,
)

NOMBRES = [
    "Mateo", "Sofia", "Thiago", "Valentina", "Benjamin", "Martina", "Lucas", "Emma",
    "Tomas", "Catalina", "Joaquin", "Renata", "Franco", "Julieta", "Agustin", "Mia",
    "Nicolas", "Olivia", "Lautaro", "Camila", "Bruno", "Isabella", "Facundo", "Alma",
    "Santino", "Victoria", "Maximo", "Pilar", "Dylan", "Bianca", "Valentin", "Clara",
    "Iker", "Antonella", "Gael", "Lara", "Felipe", "Ambar", "Bautista", "Josefina",
]
APELLIDOS = [
    "Gonzalez", "Rodriguez", "Fernandez", "Lopez", "Martinez", "Perez", "Sanchez", "Romero",
    "Diaz", "Torres", "Alvarez", "Ruiz", "Sosa", "Castro", "Ortiz", "Silva",
    "Molina", "Suarez", "Blanco", "Rojas",
]


def limpiar_base():
    for tabla in (alumno_equipo, campeonato_categoria, campeonato_equipo):
        db.session.execute(tabla.delete())
    for modelo in (EventoAgenda, Partido, Posicion, AlumnoCampeonato, Pago, Alumno,
                   Entrenamiento, Equipo, Campeonato, Categoria, Configuracion):
        db.session.query(modelo).delete()
    db.session.commit()


def obtener_categorias():
    rangos = [
        ("7", 6, 7), ("9", 8, 9), ("11", 10, 11),
        ("13", 12, 13), ("15", 14, 15), ("17", 16, 17),
        ("19", 18, 19), ("Ascenso", None, None),
    ]
    categorias = {}
    for nombre, edad_min, edad_max in rangos:
        categoria = Categoria(nombre=nombre, edad_min=edad_min, edad_max=edad_max)
        db.session.add(categoria)
        categorias[nombre] = categoria
    db.session.flush()
    return categorias


def cargar():
    categorias = obtener_categorias()
    equipos = {}
    for letra in ("A", "B", "C"):
        equipo = Equipo(nombre=letra)
        db.session.add(equipo)
        equipos[letra] = equipo
    db.session.flush()

    db.session.add(Configuracion(monto_mensualidad=85000))
    alumnos = []
    nombres_categorias = list(categorias)
    edades = {"7": 7, "9": 9, "11": 11, "13": 13,
              "15": 15, "17": 17, "19": 19, "Ascenso": 20}
    for indice, nombre in enumerate(NOMBRES):
        nombre_categoria = nombres_categorias[indice % len(nombres_categorias)]
        edad = edades[nombre_categoria]
        nacimiento = date(2026 - edad, 2 + indice % 9, 3 + indice % 24)
        alumno = Alumno(
            nombre=nombre,
            apellido=APELLIDOS[indice % len(APELLIDOS)],
            fecha_nacimiento=nacimiento,
            ci=f"SEED-{indice + 1:04d}",
            direccion=f"Barrio Deportivo {1 + indice % 8}",
            tutor=f"Familia {APELLIDOS[indice % len(APELLIDOS)]}",
            telefono=f"09{10000000 + indice:08d}",
            estado="Activo" if indice % 9 else "Retirado",
            posicion=("POR", "DEF", "MED", "DEL")[indice % 4],
            pierna_habil=("Derecha", "Izquierda", "Ambas")[indice % 3],
            peso=round(28 + (indice % 18) * 1.7, 1),
            estatura=round(1.22 + (indice % 20) * .035, 2),
            sexo="F" if indice % 3 == 1 else "M",
            beca=("Completa" if indice % 13 == 0 else "Media" if indice % 7 == 0 else "Ninguna"),
            id_categoria=categorias[nombre_categoria].id_categoria,
            categoria_manual=True,
            fecha_base_pago=date(2026, 4, 5 + indice % 20),
        )
        alumno.equipos = [equipos[("A", "B", "C")[indice % 3]]]
        db.session.add(alumno)
        alumnos.append(alumno)
    db.session.flush()

    for indice, alumno in enumerate(alumnos):
        for mes in (4, 5, 6):
            fecha_pago = date(2026, mes, 5 + indice % 20)
            es_beca = alumno.beca == "Completa" or (mes == 6 and indice % 11 == 0)
            db.session.add(Pago(
                alumno=alumno, es_beca=es_beca, fecha_pago=fecha_pago,
                fecha_vencimiento=fecha_pago + relativedelta(months=1),
                mes_pagado=f"2026-{mes:02d}", modo_pago="QR" if indice % 2 else "Efectivo",
                monto=0 if es_beca else (42500 if alumno.beca == "Media" else 85000),
            ))

    campeonatos = []
    definiciones = [
        ("Copa Apertura 2026", date(2026, 8, 8), date(2026, 10, 18), "Complejo Los Ceibos", "Planificado"),
        ("Liga Metropolitana 2026", date(2026, 5, 10), date(2026, 7, 26), "Estadio Municipal", "En curso"),
    ]
    for nombre, inicio, fin, lugar, estado in definiciones:
        campeonato = Campeonato(nombre=nombre, fecha_inicio=inicio, fecha_fin=fin, lugar=lugar, estado=estado)
        campeonato.categorias = [categorias[nombre_categoria] for nombre_categoria in nombres_categorias[:7]]
        campeonato.equipos = list(equipos.values())
        db.session.add(campeonato)
        campeonatos.append(campeonato)
    db.session.flush()

    for campeonato in campeonatos:
        for alumno in alumnos:
            if alumno.id_categoria in {cat.id_categoria for cat in campeonato.categorias} and alumno.id_alumno % 4 != 0:
                db.session.add(AlumnoCampeonato(alumno=alumno, campeonato=campeonato, habilitado=True))

    for indice, campeonato in enumerate(campeonatos):
        for partido_numero in range(12):
            categoria = campeonato.categorias[partido_numero % len(campeonato.categorias)]
            equipo = equipos[("A", "B", "C")[partido_numero % 3]]
            rival = equipos[("B", "C", "A")[partido_numero % 3]]
            fecha = campeonato.fecha_inicio + relativedelta(days=partido_numero * 7)
            partido = Partido(
                fecha=fecha, hora=time(9 + partido_numero % 5, 30), cancha=campeonato.lugar,
                id_equipo=equipo.id_equipo, id_categoria=categoria.id_categoria,
                rival=rival.nombre, id_campeonato=campeonato.id_campeonato,
                resultado=f"{partido_numero % 4}-{(partido_numero + 1) % 3}" if partido_numero < 4 else None,
            )
            db.session.add(partido)
            db.session.flush()
            db.session.add(EventoAgenda(
                fecha=partido.fecha, hora=partido.hora, descripcion=f"Partido vs {partido.rival}",
                lugar=partido.cancha, id_categoria=partido.id_categoria, id_equipo=partido.id_equipo,
                tipo="Partido", id_partido=partido.id_partido,
            ))

    descripciones = [
        ("Reunion de familias - Categoria 9", "Sala principal", "9"),
        ("Evaluacion fisica general - Categoria 13", "Pista atletica", "13"),
        ("Charla de nutricion deportiva", "Aula 2", None),
        ("Entrega de indumentaria - Categoria 15", "Sede central", "15"),
        ("Jornada abierta de captacion", "Cancha auxiliar", None),
        ("Reunion tecnica de entrenadores", "Sala principal", None),
        ("Fotos oficiales de temporada - Categoria 11", "Sede central", "11"),
        ("Torneo interno de cierre - Categoria 17", "Complejo Los Ceibos", "17"),
    ]
    for indice, (descripcion, lugar, nombre_categoria) in enumerate(descripciones):
        categoria = categorias[nombre_categoria] if nombre_categoria else None
        db.session.add(EventoAgenda(
            fecha=date(2026, 8, 1 + indice * 3), hora=time(17 + indice % 3, 0),
            descripcion=descripcion, lugar=lugar,
            id_categoria=categoria.id_categoria if categoria else None,
            tipo="Evento",
        ))

    for dia in range(7):
        db.session.add(Entrenamiento(
            dia_semana=dia, hora_inicio=time(16 + dia % 2, 0), hora_fin=time(17 + dia % 2, 30),
            lugar="Complejo Los Ceibos", id_categoria=categorias[nombres_categorias[dia % 7]].id_categoria,
            id_equipo=equipos[("A", "B", "C")[dia % 3]].id_equipo,
        ))
    db.session.commit()
    print(f"Seed cargada: {len(alumnos)} alumnos, {len(Pago.query.all())} pagos, 2 campeonatos, 24 partidos y {len(descripciones)} eventos propios.")


def main():
    parser = argparse.ArgumentParser(description="Carga datos demo de Academia de Futbol")
    parser.add_argument("--reset", action="store_true", help="Borra los datos actuales antes de cargar la seed")
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        if args.reset:
            limpiar_base()
        elif Alumno.query.count() or Campeonato.query.count():
            raise SystemExit("La base ya contiene datos. Usa --reset si quieres reemplazarla.")
        cargar()


if __name__ == "__main__":
    main()
