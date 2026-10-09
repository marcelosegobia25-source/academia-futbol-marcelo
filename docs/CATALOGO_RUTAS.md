# Catálogo de rutas HTTP

Inventario generado y contrastado con `app.url_map` el 16 de agosto de 2026. `GET` consulta o presenta formularios; `POST` modifica estado y exige CSRF. Las rutas `GET,POST` presentan y procesan el mismo formulario.

## Núcleo y acceso

| Métodos | Ruta | Endpoint |
|---|---|---|
| GET | `/` | `index` |
| GET, POST | `/acceso/` | `autenticacion.login` |
| POST | `/acceso/salir` | `autenticacion.logout` |

## Información, configuración y usuarios

| Métodos | Ruta | Endpoint |
|---|---|---|
| GET | `/informacion/` | `informacion.general` |
| GET | `/informacion/recaudacion-mes` | `informacion.recaudacion_mes` |
| GET | `/informacion/auditoria` | `informacion.auditoria` |
| POST | `/informacion/auditoria/reparar-vinculos-caja` | `informacion.reparar_vinculos_caja` |
| POST | `/informacion/respaldo-completo` | `informacion.respaldo_completo` |
| POST | `/informacion/abrir-descargas` | `informacion.abrir_descargas` |
| GET | `/configuracion/` | `configuracion.panel` |
| GET, POST | `/configuracion/mensualidad` | `configuracion.mensualidad` |
| GET, POST | `/configuracion/contrasena` | `configuracion.contrasena` |
| GET | `/configuracion/logo` | `configuracion.logo` |
| GET | `/usuarios/` | `usuarios.listar` |
| POST | `/usuarios/nuevo` | `usuarios.nuevo` |
| POST | `/usuarios/<id>/actualizar` | `usuarios.actualizar` |
| POST | `/usuarios/<id>/restablecer` | `usuarios.restablecer` |
| POST | `/usuarios/roles/<id>/permisos` | `usuarios.permisos_rol` |

## Alumnos, categorías, equipos y lugares

| Métodos | Ruta | Endpoint |
|---|---|---|
| GET | `/alumnos/` | `alumnos.listar` |
| GET, POST | `/alumnos/nuevo` | `alumnos.crear` |
| GET | `/alumnos/<id>` | `alumnos.detalle` |
| GET, POST | `/alumnos/<id>/editar` | `alumnos.editar` |
| POST | `/alumnos/<id>/eliminar` | `alumnos.eliminar` |
| POST | `/alumnos/<id>/recalcular-categoria` | `alumnos.recalcular_categoria` |
| GET | `/alumnos/<id>/foto` | `alumnos.foto_privada` |
| GET | `/alumnos/<id>/ficha.pdf` | `alumnos.ficha_pdf` |
| GET | `/alumnos/equipos-por-categoria` | `alumnos.equipos_por_categoria` |
| GET | `/alumnos/exportar` | `alumnos.exportar_excel` |
| GET | `/alumnos/exportar.pdf` | `alumnos.exportar_pdf` |
| GET | `/categorias/` | `categorias.listar` |
| GET, POST | `/categorias/nuevo` | `categorias.crear` |
| GET, POST | `/categorias/<id>/editar` | `categorias.editar` |
| POST | `/categorias/<id>/eliminar` | `categorias.eliminar` |
| GET | `/equipos/` | `equipos.listar` |
| GET, POST | `/equipos/nuevo` | `equipos.crear` |
| GET, POST | `/equipos/<id>/editar` | `equipos.editar` |
| POST | `/equipos/<id>/eliminar` | `equipos.eliminar` |
| GET | `/lugares/` | `lugares.listar` |
| GET, POST | `/lugares/nuevo` | `lugares.crear` |
| GET, POST | `/lugares/<id>/editar` | `lugares.editar` |
| POST | `/lugares/<id>/eliminar` | `lugares.eliminar` |

## Mensualidades y caja

| Métodos | Ruta | Endpoint |
|---|---|---|
| GET | `/pagos/` | `pagos.listar` |
| GET, POST | `/pagos/alumno/<id>/nuevo` | `pagos.crear` |
| POST | `/pagos/alumno/<id>/fecha-base` | `pagos.cambiar_fecha_base` |
| GET | `/pagos/<id>/comprobante` | `pagos.comprobante` |
| GET | `/pagos/<id>/recibo.pdf` | `pagos.recibo_pdf` |
| POST | `/pagos/<id>/eliminar` | `pagos.eliminar` |
| GET, POST | `/pagos/caja` | `pagos.caja` |
| POST | `/pagos/caja/abrir` | `pagos.abrir_caja` |
| POST | `/pagos/caja/<id>/reabrir` | `pagos.reabrir_caja` |
| GET | `/pagos/exportar-form` | `pagos.exportar_form` |
| GET | `/pagos/exportar` | `pagos.exportar` |
| GET | `/pagos/exportar.pdf` | `pagos.exportar_pdf` |
| GET | `/pagos/resumen-6-meses.xlsx` | `pagos.resumen_seis_meses_excel` |
| GET | `/pagos/resumen-6-meses.pdf` | `pagos.resumen_seis_meses_pdf` |

## Finanzas, recurrencias y proveedores

| Métodos | Ruta | Endpoint |
|---|---|---|
| GET | `/gestion/contabilidad` | `gestion.contabilidad` |
| GET, POST | `/gestion/contabilidad/nuevo` | `gestion.movimiento_nuevo` |
| POST | `/gestion/contabilidad/<id>/anular` | `gestion.movimiento_anular` |
| GET | `/gestion/contabilidad/<id>/comprobante` | `gestion.movimiento_comprobante` |
| GET, POST | `/gestion/contabilidad/categorias` | `gestion.categorias_contables` |
| POST | `/gestion/contabilidad/categorias/<id>/tipo` | `gestion.categoria_contable_tipo` |
| GET | `/gestion/contabilidad/exportar.csv` | `gestion.contabilidad_csv` |
| GET | `/gestion/contabilidad/exportar.pdf` | `gestion.contabilidad_pdf` |
| GET | `/gestion/contabilidad/exportar.xlsx` | `gestion.contabilidad_excel` |
| GET | `/gestion/reportes/<modulo>` | `gestion.reporte_exportar_form` |
| GET | `/gestion/pagos-programados` | `gestion.pagos_programados` |
| GET, POST | `/gestion/pagos-programados/nuevo` | `gestion.pago_programado_nuevo` |
| GET, POST | `/gestion/pagos-programados/<id>/editar` | `gestion.pago_programado_editar` |
| POST | `/gestion/pagos-programados/<id>/estado` | `gestion.pago_programado_estado` |
| POST | `/gestion/pagos-programados/generar` | `gestion.pagos_programados_generar` |
| POST | `/gestion/pagos-programados/cuota/<id>/pagar` | `gestion.cuota_programada_pagar` |
| POST | `/gestion/pagos-programados/cuota/<id>/omitir` | `gestion.cuota_programada_omitir` |
| GET | `/gestion/pagos-programados/exportar.<formato>` | `gestion.pagos_programados_exportar` |
| GET, POST | `/gestion/proveedores` | `gestion.proveedores` |
| POST | `/gestion/proveedores/<id>/estado` | `gestion.proveedor_estado` |

## Inventario, compras y ventas

| Métodos | Ruta | Endpoint |
|---|---|---|
| GET | `/gestion/inventario` | `gestion.inventario` |
| GET, POST | `/gestion/inventario/producto` | `gestion.producto_nuevo` |
| POST | `/gestion/inventario/producto/<id>/estado` | `gestion.producto_estado` |
| POST | `/gestion/inventario/<producto>/variante` | `gestion.variante_nueva` |
| POST | `/gestion/inventario/<variante>/movimiento` | `gestion.inventario_movimiento` |
| GET, POST | `/gestion/inventario/conteo` | `gestion.inventario_conteo` |
| POST | `/gestion/inventario/conteo/<id>/aprobar` | `gestion.inventario_conteo_aprobar` |
| GET | `/gestion/inventario/exportar.<formato>` | `gestion.inventario_exportar` |
| GET | `/gestion/compras` | `gestion.compras` |
| GET, POST | `/gestion/compras/nueva` | `gestion.compra_nueva` |
| POST | `/gestion/compras/<id>/anular` | `gestion.compra_anular` |
| GET | `/gestion/compras/exportar.<formato>` | `gestion.compras_exportar` |
| GET | `/gestion/ventas` | `gestion.ventas` |
| GET, POST | `/gestion/ventas/nueva` | `gestion.venta_nueva` |
| POST | `/gestion/ventas/<id>/devolver` | `gestion.venta_devolver` |
| POST | `/gestion/ventas/<id>/anular` | `gestion.venta_anular` |
| GET | `/gestion/ventas/<id>/recibo.pdf` | `gestion.venta_recibo` |
| GET | `/gestion/ventas/exportar.<formato>` | `gestion.ventas_exportar` |

## Partidos y Agenda

| Métodos | Ruta | Endpoint |
|---|---|---|
| GET | `/partidos/` | `partidos.listar` |
| GET, POST | `/partidos/nuevo` | `partidos.crear` |
| GET, POST | `/partidos/<id>/editar` | `partidos.editar` |
| POST | `/partidos/<id>/eliminar` | `partidos.eliminar` |
| POST | `/partidos/convocatoria.pdf` | `partidos.convocatoria_pdf` |
| GET | `/agenda/` | `agenda.listar` |
| GET, POST | `/agenda/nuevo` | `agenda.crear` |
| GET, POST | `/agenda/<id>/editar` | `agenda.editar` |
| POST | `/agenda/<id>/eliminar` | `agenda.eliminar` |

## Calendario, entrenamiento y asistencia

| Métodos | Ruta | Endpoint |
|---|---|---|
| GET | `/calendario/` | `calendario.ver` |
| GET | `/calendario/exportar-mensual.pdf` | `calendario.exportar_mensual_pdf` |
| GET | `/calendario/exportar-semanal.pdf` | `calendario.exportar_semanal_pdf` |
| GET | `/calendario/entrenamientos` | `calendario.listar_entrenamientos` |
| GET, POST | `/calendario/entrenamientos/nuevo` | `calendario.crear_entrenamiento` |
| GET, POST | `/calendario/entrenamientos/<id>/editar` | `calendario.editar_entrenamiento` |
| POST | `/calendario/entrenamientos/<id>/eliminar` | `calendario.eliminar_entrenamiento` |
| GET, POST | `/calendario/entrenamientos/<id>/asistencia` | `calendario.asistencia` |
| GET | `/calendario/entrenamientos/<id>/asistencia/exportar` | `calendario.asistencia_exportar_form` |
| GET | `/calendario/entrenamientos/<id>/asistencia/exportar.<formato>` | `calendario.asistencia_exportar` |
| GET, POST | `/calendario/personal` | `calendario.personal` |
| POST | `/calendario/personal/<id>/estado` | `calendario.personal_estado` |

## Campeonatos

| Métodos | Ruta | Endpoint |
|---|---|---|
| GET | `/campeonatos/` | `campeonatos.listar` |
| GET, POST | `/campeonatos/nuevo` | `campeonatos.crear` |
| GET | `/campeonatos/<id>` | `campeonatos.detalle` |
| GET, POST | `/campeonatos/<id>/editar` | `campeonatos.editar` |
| POST | `/campeonatos/<id>/finalizar` | `campeonatos.finalizar` |
| POST | `/campeonatos/<id>/reabrir` | `campeonatos.reabrir` |
| POST | `/campeonatos/<id>/categorias/<categoria>/configurar` | `campeonatos.configurar_categoria` |
| POST | `/campeonatos/<id>/generar-fixture` | `campeonatos.generar_fixture` |
| POST | `/campeonatos/<id>/eliminatorias/generar` | `campeonatos.generar_eliminatorias` |
| GET, POST | `/campeonatos/<id>/partidos/nuevo` | `campeonatos.crear_partido_manual` |
| GET, POST | `/campeonatos/<id>/partidos/<partido>/editar` | `campeonatos.editar_partido_manual` |
| POST | `/campeonatos/<id>/partidos/<partido>/eliminar` | `campeonatos.eliminar_partido_manual` |
| POST | `/campeonatos/partidos/<id>/resultado` | `campeonatos.registrar_resultado` |
| POST | `/campeonatos/partidos/<id>/walkover` | `campeonatos.registrar_walkover` |
| GET | `/campeonatos/<id>/jugadores` | `campeonatos.jugadores` |
| POST | `/campeonatos/<id>/jugadores/<alumno>/toggle` | `campeonatos.toggle_jugador` |
| GET | `/campeonatos/rivales` | `campeonatos.rivales` |
| GET, POST | `/campeonatos/rivales/nuevo` | `campeonatos.crear_rival` |
| GET, POST | `/campeonatos/rivales/<id>/editar` | `campeonatos.editar_rival` |
| POST | `/campeonatos/rivales/<id>/eliminar` | `campeonatos.eliminar_rival` |
| GET | `/campeonatos/<id>/fixture.pdf` | `campeonatos.exportar_fixture_pdf` |
| GET | `/campeonatos/<id>/fixture.xlsx` | `campeonatos.exportar_fixture_excel` |
| GET | `/campeonatos/<id>/posiciones.pdf` | `campeonatos.exportar_posiciones_pdf` |
| GET | `/campeonatos/<id>/posiciones.xlsx` | `campeonatos.exportar_posiciones_excel` |
| GET | `/campeonatos/<id>/resumen.csv` | `campeonatos.exportar_resumen` |
| GET | `/campeonatos/<id>/resumen.pdf` | `campeonatos.exportar_resumen_pdf` |
| GET | `/campeonatos/<id>/resumen.xlsx` | `campeonatos.exportar_resumen_excel` |

## Convenciones de respuesta

- HTML completo para navegación normal.
- Fragmentos HTML para filtros HTMX.
- Redirección PRG (`POST → redirect → GET`) después de cambios exitosos.
- `403` para permiso insuficiente, `404` para recurso inexistente y `500` con rollback para error no controlado.
- `send_file`/respuesta adjunta para PDF, XLSX, CSV, fotos, comprobantes y respaldos.
