# 📑 Informe de Auditoría de Flujos de Negocio y Usuario

Este informe detalla los resultados de la auditoría integral realizada sobre los **6 flujos operativos principales** de la aplicación **Academia de Fútbol**, evaluando la lógica de negocio, consistencia en base de datos, seguridad y experiencia de usuario.

---

## 📊 1. Resumen Ejecutivo de la Auditoría

| Flujo de Negocio | Casos de Uso Auditados | Estado | Observación |
| :--- | :--- | :---: | :--- |
| **1. Seguridad y Acceso** | Protección de rutas, login, credenciales, bloqueo | ✅ 100% OK | Sesiones aisladas, hash seguro, control de 5 dígitos |
| **2. Ciclo de Vida del Alumno** | Inscripción, categorización, edición, retiro, reactivación | ✅ 100% OK | Trazabilidad en historial, cálculo de edad exacto |
| **3. Tesorería y Cobranzas** | Cobro efectivo/QR, vigencia, continuidad, cierre de caja | ✅ 100% OK | Arqueo cuadrado, seguimiento de obligaciones |
| **4. Torneos y Deporte** | Creación de torneo, partidos, goles, tabla de posiciones | ✅ 100% OK | Recálculo automático de PJ, PG, PE, PP, GF, GC, PTS |
| **5. Agenda y Calendario** | Horarios semanales, eventos, turnos, calendario | ✅ 100% OK | Consistencia de turnos (Mañana/Tarde/Noche) |
| **6. Configuración y Auditoría** | Parámetros del club, bitácora inmutable de cambios | ✅ 100% OK | Registro de actor, valor anterior y nuevo |

**Resultado Global:** **17 de 17 flujos evaluados superados con éxito (100.0%)**.

---

## 🔍 2. Detalle Técnico por Flujo de Negocio

### 🛡️ Flujo 1: Autenticación y Control de Acceso
- **Protección de rutas:** Peticiones de usuarios anónimos a cualquier módulo interno (`/alumnos/`, `/pagos/`, `/campeonatos/`) son interceptadas por `@app.before_request` y redirigidas a la pantalla de login (`/acceso/?next=...`).
- **Validación de credenciales:** Se verificó la autenticación con el usuario `admin` y la contraseña `99999` mediante PBKDF2/SHA256 (`check_password_hash`).
- **Resistencia a intentos erróneos:** Peticiones con claves incorrectas son rechazadas con código 200 y mensaje visible de error sin exponer información de la base de datos.
- **Excepciones públicas:** Solo la ruta estática (`/static`), el endpoint de autenticación (`/acceso/`) y el healthcheck para la nube (`/health`) están exentos de requerir sesión activa.

---

### 🏃 Flujo 2: Ciclo de Vida del Alumno
- **Inscripción y Categorización Automática:** Si la fecha de nacimiento corresponde a un alumno de 12 años, el sistema calcula la edad cronológica exacta y le asigna la categoría correspondiente (ej. Sub-13) si no se especifica asignación manual.
- **Trazabilidad Inmutable:** Cada modificación de turno, posición, peso o estatura genera un registro en `HistorialAlumno` indicando el valor anterior y el nuevo.
- **Retiro sin Deuda Ficticia:** Al retirar a un alumno, su estado pasa a `Retirado` y su propiedad `estado_mensualidad` devuelve `Retirado`. Esto evita que un ex-alumno figure como moroso en las listas de cobranza.
- **Reactivación Limpia:** Al reactivar una matrícula, se establece `fecha_ultima_reactivacion = date.today()`. El cálculo de morosidad toma esta fecha como punto de partida, preservando el historial financiero antiguo pero sin exigir pagos de los meses en que estuvo retirado.

---

### 💳 Flujo 3: Tesorería, Cobranzas y Arqueo Diario
- **Emisión de Pagos:** El sistema acepta cobros en `Efectivo` o `QR`, genera el registro de `Pago` y vincula la cuota con su respectiva `Obligacion` a través de `AplicacionPago`.
- **Cálculo de Continuidad de Vencimientos:** La fecha de vencimiento respeta el día base de inscripción del alumno (ej. si paga el día 10, su vencimiento se calcula para el día 10 del mes siguiente).
- **Semáforo de Morosidad:**
  - `Vigente`: Fecha actual anterior al vencimiento y fuera de la ventana de aviso.
  - `Próximo a vencer`: Restan 5 días o menos para el vencimiento.
  - `Vencido`: Fecha actual posterior al vencimiento.
  - `Pagado`: Historial pasado sin deudas activas.
- **Arqueo y Cierre Diario de Caja:** En la vista de caja, se calculan por separado las sumas de `Efectivo` y `QR`. El usuario ingresa el monto físico contado y el sistema calcula la `diferencia` automáticamente, registrando el cierre de forma auditable.

---

### ⚽ Flujo 4: Torneos, Fixtures y Partidos
- **Configuración de Torneo:** Creación en formato `Liga`, `Eliminación directa` o `Mixto`, asociando múltiples categorías deportivas y equipos competidores.
- **Registro de Resultados:** Tras finalizar un partido e ingresar los goles (ej. `3 - 1`):
  - Se valida el ganador según goles regulares o penales.
  - Se actualiza la tabla de posiciones (`Posicion`) sumando los 3 puntos por victoria al ganador, 0 al perdedor (o 1 por empate), ajustando goles a favor, goles en contra y diferencia de goles (`DG`).
  - Si el formato incluye eliminatorias, el equipo ganador avanza automáticamente en la llave (`id_partido_origen_local` / `id_partido_origen_visita`).

---

### 📅 Flujo 5: Agenda, Calendario y Entrenamientos
- **Recurrencia Semanal:** Configuración de entrenamientos con día de la semana (0 a 6), hora de inicio, hora de fin y cancha.
- **Derivación de Turnos:** El sistema infiere el turno operativo (`Mañana`, `Tarde`, `Noche`) según la hora de inicio para sincronizarlo con la ficha del alumno.
- **Integración de Calendario:** El calendario mensual unifica en una sola vista con etiquetas de color:
  - 🔵 Partidos oficiales y amistosos.
  - 🟡 Entrenamientos fijos y sesiones.
  - 🟢 Torneos y campeonatos.
  - 🔷 Eventos especiales y reuniones.

---

### ⚙️ Flujo 6: Configuración y Auditoría
- **Auditoría Transversal:** Cada acción sensible (crear alumno, modificar ficha, retirar, registrar cobro, anular pago, modificar configuración) dispara un listener en SQLAlchemy que almacena en la tabla `Auditoria`:
  - `modulo`: Módulo donde ocurrió.
  - `accion`: Operación ejecutada.
  - `entidad` / `id_entidad`: Objeto afectado.
  - `id_usuario`: Actor que ejecutó la acción.
  - `valor_anterior` y `valor_nuevo`.
- **Configuración Institucional:** Los cambios de nombre de academia, cuota base de mensualidad, colores institucionales y logo se propagan dinámicamente a todas las vistas mediante `app.context_processor`.

---

## 🛠️ Cómo Repetir la Auditoría en Cualquier Momento

Puedes ejecutar la auditoría automatizada de flujos desde tu terminal cuando lo desees con el siguiente comando:

```powershell
.\.venv\Scripts\python.exe scripts/auditoria_flujos.py
```
