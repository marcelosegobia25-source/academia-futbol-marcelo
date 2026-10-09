def construir_resumen_categorias(categorias, equipos, alumnos, solo_activos=False):
    """Construye el detalle categoría → equipos → integrantes.

    Un equipo sin categoría es general y está disponible en todas. Para ese
    equipo se cuentan, dentro de cada categoría, únicamente los alumnos cuya
    categoría principal coincide. Un equipo específico aporta todos sus
    integrantes a la categoría a la que pertenece.
    """
    if solo_activos:
        alumnos = [alumno for alumno in alumnos if alumno.estado == "Activo"]
    alumnos_por_id = {alumno.id_alumno: alumno for alumno in alumnos}
    resumen = []

    for categoria in categorias:
        equipos_categoria = [
            equipo for equipo in equipos
            if equipo.id_categoria is None
            or equipo.id_categoria == categoria.id_categoria
        ]
        integrantes_equipos = []
        ids_en_equipos = set()

        for equipo in equipos_categoria:
            if equipo.id_categoria is None:
                integrantes = {
                    alumno.id_alumno: alumno
                    for alumno in equipo.alumnos
                    if (not solo_activos or alumno.estado == "Activo")
                    if alumno.id_categoria == categoria.id_categoria
                }
            else:
                integrantes = {
                    alumno.id_alumno: alumno
                    for alumno in equipo.alumnos
                    if not solo_activos or alumno.estado == "Activo"
                }
            ids_en_equipos.update(integrantes)
            integrantes_equipos.append({
                "equipo": equipo,
                "total": len(integrantes),
                "activos": sum(
                    1 for alumno in integrantes.values()
                    if alumno.estado == "Activo"
                ),
            })

        ids_categoria = {
            alumno.id_alumno
            for alumno in alumnos
            if alumno.id_categoria == categoria.id_categoria
        }
        ids_categoria.update(ids_en_equipos)
        integrantes_categoria = {
            id_alumno: alumnos_por_id[id_alumno]
            for id_alumno in ids_categoria
            if id_alumno in alumnos_por_id
        }
        ids_sin_equipo = ids_categoria - ids_en_equipos

        resumen.append({
            "categoria": categoria,
            "total": len(integrantes_categoria),
            "activos": sum(
                1 for alumno in integrantes_categoria.values()
                if alumno.estado == "Activo"
            ),
            "retirados": sum(
                1 for alumno in integrantes_categoria.values()
                if alumno.estado == "Retirado"
            ),
            "equipos": integrantes_equipos,
            "cantidad_equipos": len(equipos_categoria),
            "sin_equipo": len(ids_sin_equipo),
        })

    return resumen
