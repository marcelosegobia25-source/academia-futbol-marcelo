# Politica de conservacion y eliminacion

El sistema conserva la trazabilidad de los datos que tengan valor historico o
financiero. La politica comun para todos los modulos es:

- Las operaciones financieras, pagos, ventas y movimientos se anulan; no se
  eliminan fisicamente.
- Los alumnos, usuarios, proveedores, productos y otros maestros utilizados se
  retiran o desactivan.
- Los partidos finalizados o con resultado y los eventos pasados se conservan.
- Los campeonatos se cierran o cancelan. Una correccion que afecte una fase
  eliminatoria posterior ya finalizada se rechaza.
- Los catalogos sin dependencias pueden eliminarse cuando la aplicacion lo
  compruebe expresamente.
- La auditoria no se elimina desde la interfaz y registra actor, fecha, accion,
  valor anterior y valor nuevo.

Toda nueva funcion debe seguir estas reglas y ejecutar en una sola transaccion
los cambios que afecten a mas de un modulo.
