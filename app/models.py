"""Fachada (Facade) unificada de modelos del dominio de la Academia de Fútbol.

Reexporta todas las entidades distribuidas en los paquetes modulares del dominio:
- app.modules.seguridad.domain.models
- app.modules.configuracion.domain.models
- app.modules.alumnos.domain.models
- app.modules.pagos.domain.models
- app.modules.deporte.domain.models
- app.modules.agenda.domain.models

Mantiene total retrocompatibilidad con las importaciones existentes en el sistema.
"""

from datetime import datetime, timezone


def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# 1. Seguridad y Control de Acceso
from app.modules.seguridad.domain.models import (
    Permiso,
    Rol,
    Usuario,
    rol_permiso,
)

# 2. Configuración del Sistema y Auditoría
from app.modules.configuracion.domain.models import (
    Auditoria,
    Configuracion,
    Lugar,
    TIPOS_LUGAR,
    obtener_ip_cliente,
)

# 3. Alumnos y Ficha Deportiva
from app.modules.alumnos.domain.models import (
    Alumno,
    AlumnoTutor,
    BecaHistorial,
    HistorialAlumno,
    HistorialCategoriaAlumno,
    HistorialEquipoAlumno,
    InscripcionGestion,
    Tutor,
    alumno_equipo,
    ESTADOS_ALUMNO,
    POSICIONES,
    PIERNAS,
    SEXOS,
    BECAS,
    TURNOS,
)

# 4. Deporte: Categorías, Equipos, Partidos y Torneos
from app.modules.deporte.domain.models import (
    AlumnoCampeonato,
    Campeonato,
    CampeonatoCategoriaConfig,
    Categoria,
    Equipo,
    Partido,
    PodioCampeonato,
    Posicion,
    campeonato_categoria,
    campeonato_equipo,
    Convocatoria,
    DetalleConvocatoria,
)

# 5. Pagos, Tesorería, Facturación e Inventario
from app.modules.pagos.domain.models import (
    ESTADOS_MENSUALIDAD,
    ESTADOS_PAGO,
    MODOS_MOVIMIENTO,
    MODOS_PAGO,
    AnulacionPago,
    AplicacionPago,
    CategoriaContable,
    CierreCaja,
    Compra,
    ConteoInventario,
    CuotaProgramada,
    DetalleCompra,
    DetalleConteoInventario,
    DetalleDevolucionVenta,
    DetalleVenta,
    DevolucionVenta,
    MovimientoCaja,
    MovimientoContable,
    MovimientoInventario,
    Obligacion,
    Pago,
    PagoProgramado,
    Producto,
    ProductoVariante,
    Proveedor,
    SesionCaja,
    Tarifa,
    Venta,
)

# 6. Agenda, Calendario y Entrenamientos
from app.modules.agenda.domain.models import (
    AsistenciaEntrenamiento,
    ConflictoAutorizado,
    Entrenamiento,
    EventoAgenda,
    PersonalDeportivo,
    SesionEntrenamiento,
)

__all__ = [
    "ahora_utc",
    # Seguridad
    "Permiso",
    "Rol",
    "Usuario",
    "rol_permiso",
    # Configuración
    "Configuracion",
    "Lugar",
    "Auditoria",
    "TIPOS_LUGAR",
    "obtener_ip_cliente",
    # Alumnos
    "Alumno",
    "Tutor",
    "AlumnoTutor",
    "BecaHistorial",
    "InscripcionGestion",
    "HistorialCategoriaAlumno",
    "HistorialEquipoAlumno",
    "HistorialAlumno",
    "alumno_equipo",
    "ESTADOS_ALUMNO",
    "POSICIONES",
    "PIERNAS",
    "SEXOS",
    "BECAS",
    "TURNOS",
    # Deporte
    "Categoria",
    "Equipo",
    "Partido",
    "Campeonato",
    "campeonato_categoria",
    "campeonato_equipo",
    "CampeonatoCategoriaConfig",
    "PodioCampeonato",
    "AlumnoCampeonato",
    "Posicion",
    "Convocatoria",
    "DetalleConvocatoria",
    # Pagos & Finanzas
    "MODOS_PAGO",
    "ESTADOS_PAGO",
    "ESTADOS_MENSUALIDAD",
    "MODOS_MOVIMIENTO",
    "Pago",
    "Obligacion",
    "AplicacionPago",
    "Tarifa",
    "AnulacionPago",
    "CierreCaja",
    "SesionCaja",
    "MovimientoCaja",
    "Proveedor",
    "CategoriaContable",
    "MovimientoContable",
    "Producto",
    "ProductoVariante",
    "MovimientoInventario",
    "ConteoInventario",
    "DetalleConteoInventario",
    "Compra",
    "DetalleCompra",
    "Venta",
    "DetalleVenta",
    "DevolucionVenta",
    "DetalleDevolucionVenta",
    "PagoProgramado",
    "CuotaProgramada",
    # Agenda
    "EventoAgenda",
    "Entrenamiento",
    "PersonalDeportivo",
    "SesionEntrenamiento",
    "AsistenciaEntrenamiento",
    "ConflictoAutorizado",
]
