# 🏛️ Documentación de Arquitectura Modular y Diagramas UML

Este documento describe la refactorización arquitectónica de la aplicación **Academia de Fútbol**, estructurada bajo el patrón **Modular por Dominios (Bounded Contexts)** y **Casos de Uso (Clean Architecture)**.

---

## 📐 1. Diagrama de Paquetes UML (Package Diagram)

La aplicación organiza sus responsabilidades en 6 paquetes de dominio principales. Cada paquete encapsula su capa de **Dominio (`domain`)**, **Casos de Uso (`use_cases`)** y **Controladores / Rutas (`controllers/routes`)**.

```mermaid
graph TD
    subgraph App ["📦 app (Sistema Integral)"]
        subgraph Facade ["Fachadas de Compatibilidad"]
            ModelsFacade["app.models (Facade)"]
            RoutesFacade["app.routes (Blueprints)"]
        end

        subgraph ModSeguridad ["📦 app.modules.seguridad"]
            SegDomain["domain.models\n(Usuario, Rol, Permiso)"]
            SegUseCases["use_cases\n(AutenticarUsuario, CambiarContrasena)"]
        end

        subgraph ModConfiguracion ["📦 app.modules.configuracion"]
            ConfDomain["domain.models\n(Configuracion, Lugar, Auditoria)"]
            ConfUseCases["use_cases\n(ActualizarConfiguracion)"]
        end

        subgraph ModAlumnos ["📦 app.modules.alumnos"]
            AluDomain["domain.models\n(Alumno, Tutor, Historiales)"]
            AluUseCases["use_cases\n(InscribirAlumno, ActualizarAlumno, CambiarEstado)"]
        end

        subgraph ModDeporte ["📦 app.modules.deporte"]
            DepDomain["domain.models\n(Campeonato, Partido, Categoria, Equipo, Posicion)"]
            DepUseCases["use_cases\n(CrearCampeonato, RegistrarResultado)"]
        end

        subgraph ModPagos ["📦 app.modules.pagos"]
            PagDomain["domain.models\n(Pago, Obligacion, CierreCaja, MovimientoContable)"]
            PagUseCases["use_cases\n(RegistrarPago, AnularPago, RealizarCierreCaja)"]
        end

        subgraph ModAgenda ["📦 app.modules.agenda"]
            AgeDomain["domain.models\n(Entrenamiento, EventoAgenda, Asistencia)"]
            AgeUseCases["use_cases\n(ProgramarEntrenamiento)"]
        end
    end

    ModelsFacade --> SegDomain
    ModelsFacade --> ConfDomain
    ModelsFacade --> AluDomain
    ModelsFacade --> DepDomain
    ModelsFacade --> PagDomain
    ModelsFacade --> AgeDomain

    RoutesFacade --> AluUseCases
    RoutesFacade --> PagUseCases
    RoutesFacade --> DepUseCases
    RoutesFacade --> AgeUseCases
    RoutesFacade --> SegUseCases
    RoutesFacade --> ConfUseCases
```

---

## 🎯 2. Diagramas de Casos de Uso UML (Use Case Diagrams)

### A. Casos de Uso: Gestión de Plantel y Alumnos
```mermaid
flowchart LR
    Admin((Administrador))
    Entrenador((Entrenador))

    subgraph ModuloAlumnos ["Módulo de Alumnos"]
        UC_Ins["UC-01: Inscribir Alumno"]
        UC_Act["UC-02: Actualizar Ficha y Datos"]
        UC_Ret["UC-03: Retirar Alumno"]
        UC_Rea["UC-04: Reactivar Alumno"]
        UC_Asis["UC-05: Tomar Asistencia"]
        UC_Exp["UC-06: Exportar Planilla (Excel/PDF)"]
    end

    Admin --> UC_Ins
    Admin --> UC_Act
    Admin --> UC_Ret
    Admin --> UC_Rea
    Admin --> UC_Exp
    Entrenador --> UC_Asis
    Entrenador --> UC_Act
```

### B. Casos de Uso: Tesorería y Cobranzas
```mermaid
flowchart LR
    Cajero((Cajero / Administrador))
    Sistema((Sistema / Cron))

    subgraph ModuloPagos ["Módulo de Pagos y Finanzas"]
        UC_Cobro["UC-07: Registrar Cobro de Mensualidad"]
        UC_Abono["UC-08: Registrar Abono Parcial"]
        UC_Anular["UC-09: Anular Pago con Justificación"]
        UC_Cierre["UC-10: Realizar Cierre y Arqueo Diario"]
        UC_Calculo["UC-11: Calcular Vencimientos y Cobertura"]
    end

    Cajero --> UC_Cobro
    Cajero --> UC_Abono
    Cajero --> UC_Anular
    Cajero --> UC_Cierre
    Sistema --> UC_Calculo
```

### C. Casos de Uso: Torneos, Fixtures y Partidos
```mermaid
flowchart LR
    Admin((Administrador Deportivo))

    subgraph ModuloDeporte ["Módulo de Campeonatos y Deporte"]
        UC_Camp["UC-12: Crear y Configurar Torneo"]
        UC_Fixt["UC-13: Generar Fixture Automático"]
        UC_Res["UC-14: Cargar Resultados y Goles"]
        UC_Tabla["UC-15: Actualizar Tabla de Posiciones"]
        UC_Llaves["UC-16: Avanzar Equipos en Eliminatorias"]
    end

    Admin --> UC_Camp
    Admin --> UC_Fixt
    Admin --> UC_Res
    UC_Res -.->|dispara| UC_Tabla
    UC_Res -.->|dispara| UC_Llaves
```

---

## 📊 3. Diagrama de Clases UML del Dominio (Class Diagram)

```mermaid
classDiagram
    class Alumno {
        +int id_alumno
        +string nombre
        +string apellido
        +date fecha_nacimiento
        +string ci
        +string estado
        +string turno
        +string beca
        +date fecha_base_pago
        +nombre_completo()
        +edad()
        +estado_mensualidad()
    }

    class Categoria {
        +int id_categoria
        +string nombre
        +int edad_min
        +int edad_max
        +nombre_mostrado()
    }

    class Equipo {
        +int id_equipo
        +string nombre
        +bool es_rival
        +bool activo
    }

    class Pago {
        +int id_pago
        +date fecha_pago
        +date fecha_vencimiento
        +string mes_pagado
        +string modo_pago
        +decimal monto
        +bool activo
        +estado_cobertura()
    }

    class Obligacion {
        +int id_obligacion
        +string concepto
        +string periodo
        +decimal monto_original
        +saldo()
        +estado()
    }

    class Partido {
        +int id_partido
        +date fecha
        +time hora
        +string fase
        +string estado_partido
        +int goles_local
        +int goles_visita
        +ganador_id()
    }

    class Campeonato {
        +int id_campeonato
        +string nombre
        +string formato
        +string estado
        +date fecha_inicio
    }

    class Posicion {
        +int id
        +int pj
        +int pg
        +int pe
        +int pp
        +int gf
        +int gc
        +pts()
        +dg()
    }

    class Usuario {
        +int id_usuario
        +string nombre_usuario
        +string contrasena_hash
        +bool activo
        +verificar_contrasena()
        +tiene_permiso()
    }

    class Rol {
        +int id_rol
        +string nombre
    }

    class Entrenamiento {
        +int id_entrenamiento
        +int dia_semana
        +time hora_inicio
        +time hora_fin
        +turno()
    }

    Alumno "1" --> "*" Pago : realiza
    Alumno "*" --> "*" Equipo : integra (alumno_equipo)
    Categoria "1" --> "*" Alumno : clasifica
    Categoria "1" --> "*" Equipo : agrupa
    Equipo "1" --> "*" Partido : local
    Equipo "1" --> "*" Partido : visitante
    Campeonato "1" --> "*" Partido : contiene
    Campeonato "1" --> "*" Posicion : calcula
    Usuario "*" --> "1" Rol : asignado
    Pago "1" --> "1" Obligacion : aplica
    Categoria "1" --> "*" Entrenamiento : programa
```

---

## 🚀 4. Ventajas de la Nueva Estructura Modular

1. **Separación de Responsabilidades:** La lógica de negocio ya no se encuentra dispersa en archivos gigantescos de más de 1,400 líneas, sino en clases de Casos de Uso atómicas y testeables (`InscribirAlumnoUseCase`, `RegistrarPagoUseCase`, etc.).
2. **Cero Rotura (100% Backward Compatible):** El archivo `app/models.py` funciona como un patrón **Facade**, garantizando que cualquier llamada o consulta existente (`from app.models import Alumno, Pago...`) continúe funcionando de forma transparente.
3. **Escalabilidad para Microservicios o APIs:** Cada subpaquete en `app/modules/*` puede ser expuesto fácilmente vía API REST, GraphQL o transformado en un microservicio si el proyecto escala a futuro.
