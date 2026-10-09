# CASOS DE USO
## Sistema de Gestión de Academia Deportiva

**Versión:** 1.0.0  
**Formato:** Casos de Uso Narrativos

---

## CU-001: Registrar Alumno

**Actor:** Secretaría

**Precondición:**
- Usuario autenticado
- Sesión de secretaría activa

**Flujo Principal:**

1. Secretaría selecciona **Alumnos** → **Nuevo alumno**
2. Sistema muestra formulario vacío
3. Secretaría ingresa:
   - Nombre completo
   - Apellidos
   - Cédula de identidad
   - Fecha de nacimiento
   - Género
4. Sistema valida cédula (no duplicada)
5. Secretaría sube foto (opcional)
6. Secretaría hace clic en **"Guardar"**
7. Sistema crea registro de alumno
8. Sistema asigna categoría automáticamente (por edad)
9. Sistema registra auditoría: Usuario X creó alumno Y a las Z horas
10. Sistema muestra: "✓ Alumno registrado exitosamente"
11. Retorna a lista de alumnos

**Flujo Alternativo: Cédula Duplicada**

4a. Sistema detecta cédula existe
4b. Sistema muestra: "❌ La cédula ya está registrada"
4c. Sistema sugiere: "¿Deseas ver este alumno?"
4d. Secretaría puede:
    - Ver datos del alumno existente
    - Cancelar y no registrar
    - Ingresar otra cédula

**Postcondición:**
- Alumno creado en BD
- Alumno visible en lista
- Auditoría registrada

**Frecuencia:** ~5 veces/semana

---

## CU-002: Registrar Pago

**Actor:** Tesorera/Contador

**Precondición:**
- Alumno activo existe
- Usuario autenticado

**Flujo Principal:**

1. Tesorera selecciona **Pagos** → **Nuevo pago**
2. Sistema muestra formulario
3. Tesorera busca alumno por nombre
4. Sistema muestra:
   - Nombre
   - Saldo adeudado
   - Últimos pagos
5. Tesorera ingresa:
   - Monto pagado (puede ser parcial)
   - Mes que está pagando
   - Modo de pago (Efectivo/Transferencia/Cheque)
   - Número de comprobante (si aplica)
6. Sistema valida: Monto > 0
7. Sistema calcula nuevo saldo = Obligación - Pago
8. Tesorera haz clic en **"Registrar pago"**
9. Sistema:
   - Crea registro de pago
   - Actualiza obligación
   - Suma a movimiento de caja
   - Genera recibo PDF
   - Registra auditoría
10. Sistema muestra: "✓ Pago registrado - Recibo descargado"

**Flujo Alternativo: Pago Parcial**

5a. Tesorera ingresa monto < saldo
5b. Sistema muestra: "Saldo pendiente: $150 - $50 = $100"
5c. Tesorera confirma pago parcial
5d. Flujo continúa normalmente

**Flujo Alternativo: Monto inválido**

6a. Monto = 0 o negativo
6b. Sistema muestra: "❌ Ingrese monto válido"
6c. Tesorera corrige

**Postcondición:**
- Pago registrado
- Obligación actualizada
- Recibo generado
- Auditoría registrada
- Caja actualizada

**Frecuencia:** 10-15 veces/día

---

## CU-003: Crear Campeonato

**Actor:** Entrenador/Director

**Precondición:**
- Usuario autenticado
- Al menos 1 categoría existe

**Flujo Principal:**

1. Director selecciona **Campeonatos** → **Nuevo campeonato**
2. Sistema muestra formulario
3. Director ingresa:
   - Nombre (ej: "Liga 2026 Verano")
   - Fecha inicio
   - Fecha fin
   - Formato (Liga/Eliminación/Liga+Eliminatorias/Manual)
4. Director selecciona categorías (puede multiseleccionar)
5. Director ingresa parámetros:
   - Puntos por victoria (típico 3)
   - Puntos por empate (típico 1)
   - Puntos por derrota (típico 0)
   - Vueltas (1 o 2)
   - Clasificados para semifinal (4, 8)
   - ¿Incluir tercer puesto? Sí/No
6. Director hace clic en **"Crear campeonato"**
7. Sistema valida:
   - Nombre no duplicado en período
   - Fecha inicio < fin
   - Categorías válidas
8. Sistema crea campeonato
9. **Según formato:**
   - **Liga:** Genera automáticamente todos vs todos
   - **Eliminación:** Genera bracket
   - **Liga+Eliminatorias:** Genera fase de liga + bracket final
   - **Manual:** Sin partidos (director los crea)
10. Sistema genera todos los partidos necesarios
11. Sistema registra auditoría
12. Sistema muestra: "✓ Campeonato creado - X partidos generados"

**Postcondición:**
- Campeonato creado
- Partidos generados según formato
- Tabla de posiciones inicializada en 0
- Auditoría registrada

**Frecuencia:** ~1 vez/mes

---

## CU-004: Registrar Resultado de Partido

**Actor:** Entrenador/Anotador

**Precondición:**
- Campeonato activo
- Partido programado
- Usuario autenticado

**Flujo Principal:**

1. Anotador selecciona **Campeonatos** → **Partidos**
2. Busca el partido (sin resultado aún)
3. Hace clic en el partido
4. Sistema muestra:
   - Equipo 1 vs Equipo 2
   - Fecha/Hora
   - Lugar
   - Estado: "Programado"
5. Anotador ingresa:
   - Goles Equipo 1
   - Goles Equipo 2
6. Sistema valida: Goles >= 0
7. Anotador hace clic en **"Guardar resultado"**
8. Sistema:
   - Calcula puntos según resultado:
     - Si Equipo1 > Equipo2: E1=3pts, E2=0pts
     - Si iguales: E1=1pt, E2=1pt
   - Actualiza tabla de posiciones
   - Suma goles a favor/contra
   - Cambia estado a "Finalizado"
   - Registra auditoría: "Equipo 1 (3) vs Equipo 2 (2) - Usuario X a las Z horas"
9. Sistema muestra: "✓ Resultado registrado"
10. Tabla de posiciones se actualiza automáticamente

**Flujo Alternativo: Equipo no presente**

5a. Anotador ingresa: "Walkover" (no se presentó)
5b. Sistema:
    - Equipo presente: 3 puntos
    - Equipo ausente: 0 puntos
5c. Continúa como flujo principal

**Postcondición:**
- Resultado guardado
- Tabla actualizada
- Auditoría registrada
- Partido marcado como "Finalizado"

**Frecuencia:** 5-10 veces/semana

---

## CU-005: Abrir Caja

**Actor:** Tesorera

**Precondición:**
- Caja anterior cerrada
- Usuario autenticado

**Flujo Principal:**

1. Tesorera selecciona **Caja** → **Abrir caja**
2. Sistema muestra formulario
3. Sistema muestra:
   - Cierre anterior: Monto
   - Fecha cierre anterior
4. Tesorera ingresa:
   - **Saldo inicial:** Dinero físico que hay en la caja ahora
5. Ejemplo: Cierre anterior era $1,000, ahora hay $1,000 en efectivo
6. Tesorera hace clic en **"Abrir caja"**
7. Sistema:
   - Crea sesión de caja
   - Estado: "Abierta"
   - Registra saldo inicial
   - Marca fecha/hora de apertura
   - Registra auditoría
8. Sistema muestra: "✓ Caja abierta - Saldo inicial: $1,000"
9. Tesorera puede empezar a registrar pagos

**Postcondición:**
- Caja abierta
- Saldo inicial registrado
- Auditoría registrada

**Frecuencia:** 1 vez/día

---

## CU-006: Cerrar Caja

**Actor:** Tesorera

**Precondición:**
- Caja abierta
- Usuario autenticado
- Fin de jornada

**Flujo Principal:**

1. Tesorera selecciona **Caja** → **Cerrar caja**
2. Sistema muestra:
   - Saldo inicial: $1,000
   - Movimientos del día (suma):
     - Pagos registrados: +$2,500
     - Gastos: -$200
   - Saldo teórico: $1,000 + $2,500 - $200 = $3,300
3. Tesorera cuenta dinero físico en caja
4. Tesorera ingresa: **Saldo real: $3,300**
5. Tesorera hace clic en **"Cerrar caja"**
6. Sistema compara:
   - Saldo teórico: $3,300
   - Saldo real: $3,300
   - Diferencia: $0 ✓
7. Sistema:
   - Marca caja como "Cerrada"
   - Registra fecha/hora cierre
   - Registra auditoría
   - Genera resumen del día
8. Sistema muestra: "✓ Caja cerrada exitosamente"

**Flujo Alternativo: Diferencia en dinero**

6a. Saldo real: $3,250 (falta $50)
6b. Sistema muestra: "⚠️ Diferencia detectada: -$50"
6c. Tesorera puede:
    - Buscar error (revisar movimientos)
    - Registrar diferencia como "Faltante"
    - Cancelar cierre

**Postcondición:**
- Caja cerrada
- Resumen registrado
- Auditoría registrada
- Disponible para próxima apertura

**Frecuencia:** 1 vez/día

---

## CU-007: Generar Reporte de Pagos

**Actor:** Director/Contador

**Precondición:**
- Sistema tiene datos de pagos
- Usuario autenticado

**Flujo Principal:**

1. Director selecciona **Reportes** → **Pagos**
2. Sistema muestra opciones:
   - Fecha inicio / fecha fin
   - Estado (Pagado/Pendiente/Todos)
   - Alumno (Todos o específico)
3. Director selecciona filtros
4. Director hace clic en **"Generar reporte"**
5. Sistema:
   - Calcula: Pagos realizados
   - Calcula: Total recaudado
   - Calcula: Pendiente de cobro
   - Calcula: Promedio de pago
6. Sistema muestra tabla con:
   - Alumno
   - Mes
   - Obligación
   - Pagado
   - Saldo
7. Director hace clic en **"Descargar PDF"** o **"Descargar Excel"**
8. Sistema genera archivo
9. Archivo descarga automáticamente
10. Director puede imprimir o compartir

**Postcondición:**
- Reporte generado
- Datos descargables
- Auditoría registrada (acceso al reporte)

**Frecuencia:** 2-3 veces/semana

---

## CU-008: Restaurar Desde Respaldo

**Actor:** Administrador

**Precondición:**
- Base de datos corrupta O datos errados
- Respaldo disponible
- Usuario autenticado como Admin

**Flujo Principal:**

1. Admin selecciona **Administración** → **Respaldos**
2. Sistema muestra lista de respaldos:
   - Fecha
   - Tamaño
   - Estado ("Válido" o "Verificado")
3. Admin selecciona respaldo de fecha deseada (ej: 2026-08-15)
4. Sistema muestra:
   - Fecha del respaldo
   - Hora del respaldo
   - Tamaño
   - "⚠️ Se revertirán todos los datos desde esa fecha"
5. Admin hace clic en **"Restaurar"**
6. Sistema solicita confirmación:
   - "¿Seguro? Se perderán datos desde 2026-08-15 23:00"
7. Admin confirma
8. Sistema:
   - Crea respaldo de seguridad (actual)
   - Restaura BD desde respaldo seleccionado
   - Verifica integridad
   - Reinicia aplicación
9. Sistema muestra: "✓ Base de datos restaurada exitosamente"
10. Admin verifica que datos son correctos

**Postcondición:**
- BD restaurada a fecha anterior
- Respaldo anterior guardado
- Auditoría registrada
- Datos posteriores a la restauración se pierden

**Frecuencia:** Rara (solo si hay error)

---

*Casos de Uso v1.0.0*
