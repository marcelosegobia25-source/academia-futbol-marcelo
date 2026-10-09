# MANUAL DE USUARIO
## Sistema de Gestión de Academia Deportiva

**Versión:** 1.0.0  
**Última Actualización:** 16 de Agosto de 2026  
**Audiencia:** Usuarios finales (no técnicos)

---

## 📋 TABLA DE CONTENIDOS

1. Bienvenida
2. Primeros pasos
3. Navegación general
4. Módulo Académico
5. Módulo Deportivo
6. Módulo Financiero
7. Módulo de Inventario
8. Módulo de Auditoría
9. Reportes y Exportaciones
10. Mantenimiento y Respaldos
11. Preguntas frecuentes
12. Resolución de problemas

---

## 1. BIENVENIDA

¡Bienvenido al Sistema de Gestión de Academia Deportiva!

Este manual le ayudará a utilizar todas las funciones del sistema de forma rápida y eficiente. No se requieren conocimientos técnicos.

**Requisitos:**
- Navegador web (Chrome, Firefox o Edge)
- Usuario y contraseña
- Conexión a Internet (opcional - el sistema también funciona sin conexión)

---

## 2. PRIMEROS PASOS

### 2.1 Iniciar Sesión

**Paso a paso:**

1. Abre el navegador
2. Dirígete a la dirección que proporcione el administrador
3. En la pantalla de inicio, verás dos campos:
   - Campo **Usuario**: Ingresa tu usuario
   - Campo **Contraseña**: Ingresa tu contraseña
4. Haz clic en el botón **"Iniciar sesión"**
5. Si los datos son correctos, verás el panel principal

**¿Olvidó su contraseña?**
- Contacte al administrador del sistema para restablecerla

### 2.2 Cambiar Contraseña

Para proteger tu cuenta:

1. Haz clic en tu **nombre de usuario** (arriba a la derecha)
2. Selecciona **"Cambiar contraseña"**
3. Ingresa tu contraseña actual
4. Ingresa la nueva contraseña (mínimo 8 caracteres)
5. Confirma la nueva contraseña
6. Haz clic en **"Guardar"**

---

## 3. NAVEGACIÓN GENERAL

### 3.1 Estructura de la pantalla

```
┌─────────────────────────────────────────────────┐
│  Logo          SISTEMA         [Usuario] [≡]   │ ← Encabezado
├─────────────────────────────────────────────────┤
│ ≡ Menu  │                                       │
│  ├─ Alumnos                                    │ ← Panel lateral
│  ├─ Pagos                                      │
│  ├─ Equipos                                    │
│  ├─ Campeonatos                                │
│  └─ Configuración                              │
│                                                 │
│                                                 │
│            [CONTENIDO PRINCIPAL]                │ ← Área de trabajo
│                                                 │
│                                                 │
│                                                 │
├─────────────────────────────────────────────────┤
│ © 2026 Academia Deportiva                      │ ← Pie de página
└─────────────────────────────────────────────────┘
```

### 3.2 Menús principales

**Menú Académico:**
- Alumnos
- Tutores y Apoderados
- Categorías
- Inscripciones

**Menú Deportivo:**
- Equipos
- Campeonatos
- Partidos
- Entrenamientos
- Profesores y Entrenadores

**Menú Financiero:**
- Pagos
- Obligaciones
- Caja
- Reportes Financieros

**Menú de Inventario:**
- Productos
- Compras
- Ventas
- Proveedores

**Menú de Administración:**
- Usuarios
- Configuración
- Auditoría
- Respaldos

---

## 4. MÓDULO ACADÉMICO

### 4.1 Gestión de Alumnos

#### Registrar un alumno

**¿Para qué sirve?**
Agregar un nuevo alumno al sistema.

**¿Quién puede hacerlo?**
Secretaría, Director, Administrador.

**Pasos:**

1. Ve a **Alumnos** → **Nuevo alumno**
2. Completa los datos obligatorios:
   - Nombre completo
   - Apellidos
   - Cédula de identidad
   - Fecha de nacimiento
   - Género
3. (Opcional) Sube una foto
4. Haz clic en **"Guardar"**

**¿Qué errores pueden aparecer?**
- "La cédula ya existe" → El alumno está registrado
- "El nombre es obligatorio" → Falta completar un campo requerido
- "Formato de cédula inválido" → Revisa el formato (ej: 12345678)

#### Editar datos de un alumno

1. Ve a **Alumnos**
2. Busca el alumno en la lista
3. Haz clic en el botón **[Editar]**
4. Modifica los datos
5. Haz clic en **"Guardar"**

#### Consultar ficha de alumno

1. Ve a **Alumnos**
2. Haz clic en el nombre del alumno
3. Verás:
   - Datos personales
   - Foto
   - Categoría actual
   - Equipos en los que participa
   - Historial de pagos
   - Asistencias

#### Cambiar categoría (por edad)

El sistema calcula automáticamente la categoría según edad, pero puedes cambiarla manualmente:

1. Ve a **Alumnos**
2. Busca el alumno
3. Haz clic en **[Editar]**
4. Cambia el campo **Categoría**
5. Haz clic en **"Guardar"**

#### Retirar un alumno

Cuando un alumno se va, retirarelo (no se borra):

1. Ve a **Alumnos**
2. Selecciona el alumno
3. Haz clic en **[Retirar]**
4. Confirma la acción
5. El alumno aparecerá como "Retirado"

#### Reactivar un alumno

Si un alumno quiere volver:

1. Ve a **Alumnos** (marca "Mostrar retirados")
2. Selecciona el alumno retirado
3. Haz clic en **[Reactivar]**
4. El alumno volverá a "Activo"

### 4.2 Gestión de Tutores

#### Registrar tutor

1. Ve a **Tutores y Apoderados** → **Nuevo tutor**
2. Completa:
   - Nombre completo
   - Cédula de identidad
   - Teléfono
   - Email (opcional)
3. Haz clic en **"Guardar"**

#### Asociar tutor a alumno

1. Ve a **Alumnos** → Selecciona un alumno
2. En la sección **Tutores**, haz clic en **[Agregar tutor]**
3. Selecciona un tutor de la lista
4. Indica la relación (padre, madre, tía, etc.)
5. Haz clic en **"Guardar"**

---

## 5. MÓDULO DEPORTIVO

### 5.1 Gestión de Equipos

#### Crear un equipo

1. Ve a **Equipos** → **Nuevo equipo**
2. Completa:
   - Nombre del equipo (ej: "Categoría Sub-12 A")
   - Categoría
   - Entrenador (opcional)
3. Haz clic en **"Crear"**

#### Agregar jugadores a un equipo

1. Ve a **Equipos** → Selecciona el equipo
2. En la sección **Jugadores**, haz clic en **[Agregar jugador]**
3. Busca y selecciona alumnos
4. Haz clic en **"Guardar"**

### 5.2 Gestión de Campeonatos

#### Crear un campeonato

1. Ve a **Campeonatos** → **Nuevo campeonato**
2. Completa:
   - **Nombre:** (ej: "Liga 2026 - Verano")
   - **Fecha inicio/fin**
   - **Formato:** Liga, Eliminación directa, Liga + Eliminatorias, Manual
   - **Categorías:** Selecciona qué categorías participan
   - **Vueltas:** 1 o 2 (para ligas)
   - **Puntos:** Por victoria, empate, derrota
3. Haz clic en **"Crear"**

#### Ver tabla de posiciones

1. Ve a **Campeonatos**
2. Selecciona un campeonato
3. Verás la **Tabla de Posiciones** con:
   - Equipo
   - Partidos jugados
   - Ganados/Empatados/Perdidos
   - Puntos
   - Goles a favor/contra

#### Registrar resultado de partido

1. Ve a **Campeonatos** → **Partidos**
2. Selecciona el partido no jugado
3. Ingresa:
   - Goles de tu equipo
   - Goles del rival
4. Haz clic en **"Guardar resultado"**
5. La tabla se actualiza automáticamente

### 5.3 Entrenamientos y Asistencia

#### Crear entrenamiento

1. Ve a **Calendario** → **Entrenamientos** → **Nuevo**
2. Completa:
   - Equipo
   - Día y hora
   - Lugar
   - Entrenador
3. Haz clic en **"Guardar"**

#### Registrar asistencia

1. Ve a **Calendario** → **Entrenamientos**
2. Selecciona un entrenamiento
3. Para cada alumno, marca:
   - ☑ Presente
   - ☐ Ausente
   - ☑ Justificado
   - ☑ Tarde
4. (Opcional) Agrega justificación
5. Haz clic en **"Guardar asistencia"**

---

## 6. MÓDULO FINANCIERO

### 6.1 Gestión de Pagos

#### Registrar mensualidad

1. Ve a **Pagos** → **Nuevo pago**
2. Selecciona:
   - **Alumno**
   - **Mes pagado**
   - **Año**
3. Ingresa:
   - **Monto**
   - **Modo de pago** (Efectivo, Transferencia, Cheque, etc.)
   - (Opcional) Número de comprobante
4. Haz clic en **"Registrar pago"**
5. Se genera automáticamente un recibo

#### Registrar pago parcial

Cuando un alumno paga menos de lo adeudado:

1. Ve a **Pagos** → **Nuevo pago**
2. Selecciona el alumno
3. Ingresa un monto menor al adeudado
4. Sistema detalla cuánto falta
5. Haz clic en **"Registrar"**

#### Consultar saldo de alumno

1. Ve a **Alumnos** → Selecciona un alumno
2. En la sección **Finanzas**, verás:
   - Total adeudado
   - Pagos realizados
   - Saldo pendiente

#### Anular un pago

Si se registró un pago erróneamente:

1. Ve a **Pagos**
2. Busca el pago
3. Haz clic en **[Anular]**
4. Confirma la acción
5. El pago se marca como anulado (no se borra)

#### Descargar recibo de pago

1. Ve a **Pagos**
2. Busca el pago
3. Haz clic en **[Descargar PDF]**
4. Se descarga el recibo listo para imprimir

### 6.2 Gestión de Caja

#### Abrir caja

Al inicio del día:

1. Ve a **Caja** → **Abrir caja**
2. Ingresa el **saldo inicial** (dinero físico en la caja)
3. Haz clic en **"Abrir"**
4. La caja está lista para operaciones

#### Registrar movimientos

Automático: Cada pago registrado se suma a la caja.

Manual (si necesitas registrar algo más):

1. Ve a **Caja** → **Movimientos**
2. Haz clic en **[Nuevo movimiento]**
3. Ingresa:
   - Tipo (Ingreso/Egreso)
   - Monto
   - Concepto
4. Haz clic en **"Guardar"**

#### Cerrar caja

Al final del día:

1. Ve a **Caja** → **Cerrar caja**
2. Sistema muestra:
   - Saldo inicial
   - Ingresos del día
   - Egresos del día
   - Saldo final (teórico)
3. Verifica contra el dinero físico
4. Si coincide, haz clic en **"Confirmar cierre"**
5. Si no coincide, revisa movimientos

**¿Qué pasa si no coincide?**
- Revisa los movimientos registrados
- Busca errores en los montos
- Si encuentras un error, anula ese movimiento y registra uno nuevo
- Luego intenta cerrar nuevamente

---

## 7. MÓDULO DE INVENTARIO

### 7.1 Gestión de Inventario

#### Registrar producto

1. Ve a **Inventario** → **Productos** → **Nuevo**
2. Completa:
   - Nombre del producto
   - Código (opcional)
   - Precio
   - Stock inicial
3. Haz clic en **"Guardar"**

#### Registrar entrada de mercadería

Cuando compras productos:

1. Ve a **Compras** → **Nueva compra**
2. Selecciona:
   - **Proveedor**
   - **Productos** (cantidad y precio)
3. Ingresa total
4. Haz clic en **"Guardar"**
5. El stock se actualiza automáticamente

#### Registrar venta

1. Ve a **Ventas** → **Nueva venta**
2. Selecciona los productos
3. Ingresa cantidades
4. Sistema calcula el total
5. Ingresa modo de pago
6. Haz clic en **"Guardar"**
7. Se genera recibo automático

#### Consultar stock

1. Ve a **Inventario** → **Stock**
2. Verás todos los productos con:
   - Cantidad disponible
   - Cantidad vendida
   - Precio
   - Valor total en inventario

---

## 8. MÓDULO DE AUDITORÍA

### 8.1 Panel de Auditoría

#### Ver log de operaciones

1. Ve a **Administración** → **Auditoría**
2. Verás un registro de todas las operaciones:
   - Quién realizó la acción
   - Qué hizo (crear, modificar, eliminar)
   - Cuándo
   - Datos anteriores y nuevos

#### Verificar integridad de datos

1. Ve a **Administración** → **Integridad**
2. Sistema analiza la base de datos
3. Muestra:
   - ✅ Estado general
   - Número de registros
   - Errores (si hay)
   - Respaldos disponibles

---

## 9. REPORTES Y EXPORTACIONES

### 9.1 Generar reportes

#### Reporte de alumnos

1. Ve a **Alumnos** → **Reporte**
2. Selecciona:
   - Categoría (todas o específica)
   - Estado (activos/retirados)
3. Haz clic en **"Generar"**
4. Verás la lista con todos los datos

#### Reporte de pagos

1. Ve a **Pagos** → **Reporte**
2. Selecciona:
   - Fechas
   - Estado (pagado/pendiente)
3. Sistema muestra:
   - Total recaudado
   - Pendiente de cobro
   - Valor promedio
4. Puedes **descargar en PDF o Excel**

#### Reporte de campeonato

1. Ve a **Campeonatos** → Selecciona campeonato
2. Haz clic en **[Descargar reporte]**
3. Se genera PDF con:
   - Tabla de posiciones
   - Todos los partidos
   - Goles a favor/contra
   - Estadísticas

### 9.2 Exportar datos

#### Descargar en Excel

La mayoría de listas permiten descargar:

1. Ve a cualquier módulo (Alumnos, Pagos, etc.)
2. Busca el botón **[Exportar Excel]**
3. Se descarga un archivo .xlsx que puedes:
   - Abrir en Excel
   - Imprimir
   - Modificar
   - Guardar

#### Descargar en PDF

Para reportes formales:

1. Ve a **Reportes**
2. Selecciona el reporte
3. Haz clic en **[Descargar PDF]**
4. Abre el PDF con Adobe Reader
5. Imprime si necesitas

---

## 10. MANTENIMIENTO Y RESPALDOS

### 10.1 Respaldos

**El sistema crea respaldos automáticos cada día a las 23:00 horas.**

#### Ver respaldos

1. Ve a **Administración** → **Respaldos**
2. Verás la lista con:
   - Fecha del respaldo
   - Tamaño
   - Opción de descargar

#### Descargar un respaldo

Para seguridad adicional:

1. Ve a **Respaldos**
2. Busca la fecha que quieres
3. Haz clic en **[Descargar]**
4. Se descarga el archivo .db
5. Guarda en USB o nube

#### Restaurar desde un respaldo

Si algo salió mal:

1. Ve a **Administración** → **Respaldos**
2. Selecciona la fecha
3. Haz clic en **[Restaurar]**
4. Confirma la acción
5. Sistema revierte a esa fecha
6. **ADVERTENCIA:** Se pierden los datos después de esa fecha

---

## 11. PREGUNTAS FRECUENTES

### P: ¿Qué pasa si se va la luz?
R: No hay problema. El sistema guarda todo en la base de datos cada vez que haces clic en "Guardar". Si se va la luz, pierdes solo lo que estabas escribiendo en ese momento.

### P: ¿Puedo trabajar sin Internet?
R: Sí. El sistema funciona completamente sin conexión a Internet. Solo necesita estar instalado localmente.

### P: ¿Puedo ver reportes en mi teléfono?
R: Actualmente el sistema solo funciona en navegador de computadora. En el futuro habrá versión móvil.

### P: ¿Qué pasa si me equivoco al registrar un pago?
R: No hay problema. Ve a Pagos, busca el pago, haz clic en [Anular], y registra el pago correcto. Los dos quedan en auditoría.

### P: ¿Quién puede ver todo?
R: Solo el Administrador ve todo. Los demás ven solo según sus permisos:
- Secretaría: Solo módulo académico
- Contador: Solo módulo financiero
- Entrenador: Solo módulo deportivo
- Director: Todo (excepto usuarios)

### P: ¿Dónde se guardan los datos?
R: En la carpeta: C:\ProgramData\GestionAcademiaDeportiva\academia.db

### P: ¿Puedo imprimir los reportes?
R: Sí. Todos los reportes están en PDF. Abre y presiona Ctrl+P.

### P: ¿Cuántos usuarios pueden usar el sistema a la vez?
R: Hasta 50 usuarios simultáneos sin problema.

---

## 12. RESOLUCIÓN DE PROBLEMAS

### El sistema no abre

**Posibles causas y soluciones:**

1. **El navegador no responde:**
   - Cierra el navegador completamente
   - Abre nuevamente
   - Intenta acceder

2. **Dice "No se puede conectar":**
   - Verifica que el servicio esté activo
   - Reinicia la computadora
   - Contacta al administrador

3. **Página en blanco:**
   - Limpia el caché del navegador (Ctrl+Shift+Delete)
   - Intenta con otro navegador (Firefox o Chrome)

### Olvidé mi contraseña

1. Contacta al administrador
2. Te proporcionará una contraseña temporal
3. Cámbiala en el primer inicio de sesión

### El alumno que intento registrar dice "duplicado"

1. Este alumno ya existe en el sistema
2. Busca su nombre en la lista
3. Si es necesario cambiar datos, edita ese registro

### No puedo hacer clic en un botón

1. Puede deberse a falta de permisos
2. Solo ciertos usuarios pueden hacer ciertas operaciones
3. Contacta al administrador si crees que deberías tener acceso

### Los números se ven extraños

1. Es un problema de formato regional
2. Contacta al administrador para cambiar la región del navegador

---

## Más Ayuda

**Para consultas adicionales:**

📧 Email: soporte@academia.com  
📞 Teléfono: [Número de contacto]  
🕐 Horario: Lunes a Viernes, 09:00 - 17:00

---

*Manual de Usuario v1.0.0 - Sistema de Gestión Academia Deportiva*
