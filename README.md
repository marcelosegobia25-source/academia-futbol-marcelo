# Academia de Fútbol — Sistema de Gestión Deportiva en la Nube (SaaS)

Plataforma web en la nube para gestionar alumnos, mensualidades, categorías,
equipos, partidos, agenda, calendario y campeonatos de una academia de fútbol.
Opera **100% en la nube**: acceso universal 24/7 desde cualquier dispositivo
(computadoras, laptops, tablets en cancha y smartphones), base de datos cloud,
respaldos automáticos continuos y cero requerimientos de instalación local.

## Características Principales Cloud

- **Acceso Multi-Dispositivo 24/7:** Compatible con PC, Mac, tablets y celulares sin instalar nada.
- **Base de Datos Cloud Segura:** Gestión integral de datos bajo motor relacional (PostgreSQL / SQLAlchemy).
- **Control Financiero Inteligente:** Semáforo de estados de pago, continuidad de cuotas y emisión de recibos oficiales en PDF.
- **Motor Deportivo Automático:** Generación de fixtures, tablas de posiciones en tiempo real y convocatorias oficiales.
- **Respaldos Automáticos en la Nube:** Copias de seguridad diarias gestionadas con retención de 30 días.

## Requisitos de Acceso para Usuarios

- Cualquier dispositivo con conexión a Internet y navegador web moderno (Chrome, Safari, Edge, Firefox).

---

## Entorno de Desarrollo y Despliegue Local (Desarrolladores)

- Python 3.10 o superior instalado en la computadora donde se usará.

## Instalación (una sola vez)

### Instalador para Windows

En otra computadora Windows de 64 bits, ejecute
`Instalador_Gestion_Academia_1.0.0.exe`. El instalador crea el acceso
directo y abre el sistema en el navegador sin requerir Python.

La instalación nueva crea una base vacía de alumnos, pagos y demás datos
operativos. Solo incluye las categorías iniciales y la configuración mínima.
Los datos persistentes se guardan en
`%LOCALAPPDATA%\GestionAcademiaDeportiva`, separados de los archivos del programa,
por lo que una actualización o desinstalación no los elimina.

Los PDF, Excel, CSV, recibos, fichas y respaldos descargados desde la
plataforma conservan una copia organizada bajo
`%LOCALAPPDATA%\GestionAcademiaDeportiva\Descargas`. Desde Información general se
puede usar el botón **Abrir Descargas**.

La contraseña inicial es `00000` y debe cambiarse en el primer uso.

### Instalación desde código fuente

1. Descomprima la carpeta del proyecto en la computadora de la academia.
2. Abra una terminal dentro de la carpeta `academia_futbol` y ejecute:

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## Uso diario

Cada vez que quiera usar el sistema:

```bash
# activar el entorno (si no está activado)
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

python serve.py
```

Luego abra el navegador en: **http://127.0.0.1:5000**

`serve.py` utiliza Waitress, un servidor estable para el uso diario. `run.py`
queda reservado para desarrollo local y sólo activa el modo debug cuando se
define explícitamente `FLASK_DEBUG=1`.

No requiere internet: todo corre en la propia computadora. La base de
datos se guarda en `instance/academia.db` — haga copias de seguridad de
ese archivo periódicamente (por ejemplo, copiándolo a un pendrive).

El sistema crea automáticamente un respaldo SQLite consistente por día en
`instance/backups/` y conserva 30 días. También puede ejecutar:

```bash
python -m scripts.backup
python -m scripts.restore instance/backups/archivo.db --confirmar
```

Antes de restaurar, el sistema valida el respaldo y conserva una copia de la
base que estaba activa.

Para crear un respaldo transportable con la base, fotografías, personalización y manifiesto de
integridad:

```bash
python -m scripts.backup_completo
```

Mantenimiento recomendado (el segundo comando solo ocasionalmente y con el
sistema cerrado):

```bash
python -m scripts.maintenance
python -m scripts.maintenance --vacuum
```

## Cargar datos de prueba

La seed está separada de la aplicación y genera datos reproducibles para
probar filtros, reportes, agenda y campeonatos:

```bash
python -m scripts.seed --reset
```

El comando crea 40 alumnos, 3 equipos globales independientes (A, B y C), y
las categorías 7, 9, 11, 13, 15, 17, 19 y Ascenso,
120 pagos, 2 campeonatos, partidos programados, eventos de agenda y
entrenamientos semanales. `--reset` reemplaza los datos actuales de la base
local; sin esa opción, la seed se detiene si ya existen alumnos o campeonatos.

Los pagos se archivan mediante borrado lógico: al eliminarlos desde la
interfaz dejan de aparecer en listados y reportes, pero su fila permanece en
SQLite para conservar trazabilidad. La columna se agrega automáticamente al
iniciar una base existente.

## Estructura del proyecto

```
academia_futbol/
├── run.py                 # Punto de entrada (ejecutar esto)
├── config.py               # Configuración (rutas, límites de archivo)
├── requirements.txt
├── instance/
│   └── academia.db         # Base de datos SQLite (se crea sola al iniciar)
└── app/
    ├── models.py            # Todas las tablas del sistema
    ├── extensions.py
    ├── routes/              # Un archivo por módulo (alumnos, pagos, etc.)
    ├── templates/            # Vistas HTML (HTMX + Bootstrap)
    ├── utils/
    │   ├── reglas.py         # Reglas de negocio (categoría automática, vencimientos)
    │   ├── pdfs.py            # Generación de recibos PDF
    │   └── excel.py           # Exportación de pagos a Excel
    └── static/
        ├── vendor/            # HTMX y Bootstrap (locales, sin CDN)
        └── uploads/alumnos/   # Fotos de los alumnos
```

## Módulos implementados

- **Alumnos**: ficha completa (foto, datos personales, tutor(es),
  posición, pierna hábil, peso/estatura, beca, estado). La categoría se
  asigna automáticamente según la fecha de nacimiento, pero puede
  fijarse manualmente. La ficha muestra los últimos 6 pagos.
- **Mensualidades (Pagos)**: el primer pago define la fecha base de
  vencimientos (por continuidad se calculan los siguientes meses
  automáticamente). No se permite pagar dos veces el mismo mes ni
  pagos parciales. Se genera un recibo en PDF descargable
  automáticamente, y se puede exportar el historial a Excel por
  periodo o completo.
- **Categorías**: rango de edad configurable; base para la asignación
  automática de alumnos.
- **Equipos**: pueden ser globales para todas las categorías o específicos de
  una categoría. Un alumno puede pertenecer a uno o varios equipos y un mismo
  equipo global puede participar en distintas categorías.
- **Partidos**: al programarse se agregan automáticamente a la Agenda.
- **Agenda**: eventos propios + partidos programados.
- **Calendario**: vista mensual combinando agenda, campeonatos y
  entrenamientos fijos (recurrentes por día de la semana).
- **Campeonatos**: asignación de categorías/equipos participantes,
  generación automática de fixture (todos contra todos por categoría),
  carga de resultados con actualización automática de la tabla de
  posiciones, y habilitación/deshabilitación de jugadores por
  campeonato (visible también en la ficha de cada alumno).
- **Contabilidad**: ingresos y egresos manuales, además de los ingresos
  automáticos originados por mensualidades y ventas.
- **Inventario**: productos, tallas, colores, precios, existencias y alertas
  de stock mínimo.
- **Ventas**: uniformes y otros productos, asociación opcional al alumno,
  recibo PDF y restitución de existencias al anular.

## Notas sobre reglas de negocio ya implementadas

- **Categoría automática**: se calcula según la edad actual del
  alumno comparada contra el rango (`edad_min`–`edad_max`) de cada
  categoría. Se puede recalcular manualmente desde la ficha del
  alumno con el botón "Recalcular categoría por edad".
- **Vencimiento de pagos**: el primer pago usa la fecha indicada
  manualmente como base; los siguientes meses vencen exactamente un
  mes después del anterior, contando desde esa fecha base (así se
  mantiene la continuidad aunque el alumno se retire y vuelva más
  adelante — su historial se conserva).
- **Estado del pago**: Vigente / Próximo a vencer (5 días antes del
  vencimiento) / Vencido — se calcula en tiempo real, no se guarda en
  la base de datos.

## Integridad y pruebas

- SQLite inicia con claves foráneas activadas, modo WAL y espera de bloqueo.
- Las migraciones quedan registradas en `schema_migration`.
- Un índice único impide dos pagos activos para el mismo alumno y mes.
- Fixture, partidos y Agenda se mantienen sincronizados.
- Corregir un resultado reconstruye la tabla de posiciones desde cero.
- Los formularios POST están protegidos con CSRF y se validan nuevamente en
  el servidor.

Para ejecutar las pruebas:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```
