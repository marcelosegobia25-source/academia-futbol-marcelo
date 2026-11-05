# DOCUMENTO DE REQUISITOS
## Sistema de Gestión de Academia Deportiva

**Versión:** 1.0.0  
**Fecha:** 16 de Agosto de 2026

---

## 📋 REQUISITOS FUNCIONALES

### MÓDULO ACADÉMICO

#### RF-001: Registrar Alumno
- El sistema debe permitir crear un registro nuevo de alumno
- Campos: Nombre, Apellido, Cédula, Fecha Nacimiento, Género, Foto
- Validación: Cédula no duplicada
- Resultado: Alumno creado con ID único

#### RF-002: Prevenir Documentos Duplicados
- El sistema debe rechazar cédulas duplicadas
- Mensaje: "La cédula ya existe"
- Impacto: Integridad de datos

#### RF-003: Editar Información de Alumno
- El sistema debe permitir modificar datos
- Restricción: No cambiar ID ni cédula
- Auditoría: Registrar cambios

#### RF-004: Cambiar Categoría Automáticamente
- El sistema debe calcular categoría por edad
- Fórmula: Categoría = fecha_actual.year - fecha_nacimiento.year
- Manual: Permitir override manual

#### RF-005: Retirar Alumno
- El sistema debe marcar alumno como "Retirado"
- No es eliminación física
- Mantener historial

#### RF-006: Reactivar Alumno Retirado
- El sistema debe permitir reactivar
- Cambiar estado de "Retirado" a "Activo"
- Mantener datos históricos

#### RF-007: Generar Ficha Alumno en PDF
- El sistema debe generar documento con datos de alumno
- Incluir: Foto, datos, equipos, pagos, asistencias
- Formato: PDF descargable

### MÓDULO DEPORTIVO

#### RF-008: Crear Campeonato
- El sistema debe permitir crear campeonato
- Campos: Nombre, fecha inicio/fin, formato, categorías
- Formatos: Liga, Eliminación directa, Liga + Eliminatorias, Manual
- Validación: Fechas coherentes (inicio < fin)

#### RF-009: Generar Partidos Automáticamente
- Según formato seleccionado:
  - **Liga:** Todos vs Todos
  - **Eliminación:** Bracket automático
  - **Manual:** Usuario define manualmente

#### RF-010: Tabla de Posiciones
- Calcular automáticamente:
  - Partidos: J (jugados)
  - Ganados (G), Empatados (E), Perdidos (P)
  - Puntos: G×3 + E×1 + P×0 (configurable)
  - Goles: A Favor (GF), En Contra (GC), Diferencia (GF-GC)

#### RF-011: Registrar Resultado de Partido
- El sistema debe permitir ingresar: Goles equipo 1, Goles equipo 2
- Actualizar tabla automáticamente
- Registrar hora de ingreso
- Auditar cambios

#### RF-012: Registrar Asistencia a Entrenamientos
- El sistema debe registrar: Presente, Ausente, Justificado, Tarde
- Campo de justificación opcional
- Generar reportes de asistencia

### MÓDULO FINANCIERO

#### RF-013: Registrar Mensualidad
- El sistema debe crear obligación de pago
- Campos: Alumno, mes, monto, año
- Validación: Alumno activo
- Resultado: Obligación creada

#### RF-014: Registrar Pago
- El sistema debe crear registro de pago
- Campos: Alumno, monto, modo (Efectivo/Transferencia/Cheque), comprobante
- Generar recibo PDF automáticamente
- Auditar movimiento

#### RF-015: Permitir Pagos Parciales
- Alumno con obligación $100 puede pagar $50
- Sistema registra $50 como pago
- Saldo pendiente = $50
- Permite pagar resto después

#### RF-016: Anular Pago
- El sistema debe marcar pago como anulado
- No se borra (cumple auditoría)
- Se libera el monto de la caja
- Permite registrar pago correcto

#### RF-017: Generar Recibo en PDF
- Automáticamente después de registrar pago
- Contiene: Alumno, monto, fecha, modo, comprobante
- Imprimible
- Descargable

#### RF-018: Consultar Saldo de Alumno
- El sistema debe mostrar:
  - Total adeudado (Obligaciones - Pagos)
  - Detalles por mes
  - Último pago
  - Estado de cuenta

#### RF-019: Abrir Caja
- El sistema debe crear sesión de caja
- Registrar saldo inicial (dinero físico)
- Estado: "Abierta"
- Permitir movimientos

#### RF-020: Registrar Movimientos de Caja
- Automático: Cada pago se suma a caja
- Manual: Usuario puede registrar entrada/salida adicional
- Auditar cada movimiento

#### RF-021: Cerrar Caja
- El sistema debe permitir:
  - Saldo inicial + Ingresos - Egresos = Saldo final teórico
  - Usuario ingresa dinero físico contado
  - Si coinciden: Cierre exitoso
  - Si no: Mostrar diferencia y permitir ajustes

#### RF-022: Reabrir Caja Cerrada
- Si fue cerrada por error
- Sistema permite: Seleccionar caja, hac clic "Reabrir"
- Vuelve a estado "Abierta"
- Auditar acción

### MÓDULO DE INVENTARIO

#### RF-023: Registrar Producto
- El sistema debe crear registro de producto
- Campos: Nombre, código, precio, stock
- Validación: Nombre no duplicado

#### RF-024: Registrar Compra
- El sistema debe registrar entrada de mercadería
- Campos: Proveedor, productos, cantidades, precio
- Actualizar stock automáticamente
- Generar comprobante

#### RF-025: Registrar Venta
- El sistema debe crear venta
- Seleccionar productos, cantidades
- Validar stock suficiente
- Restar del stock
- Generar recibo

#### RF-026: Prevenir Stock Negativo
- El sistema NO debe permitir venta si stock < cantidad
- Mensaje: "Stock insuficiente"
- Sugerir cantidad disponible

#### RF-027: Anular Venta
- Marca como anulada
- Restaura stock
- No se borra físicamente

#### RF-028: Devolución de Venta
- Crear registro de devolución
- Relacionar con venta original
- Restaurar stock
- Reembolsar monto

### MÓDULO DE AUDITORÍA

#### RF-029: Registrar Auditoría
- El sistema debe registrar TODAS las operaciones:
  - Crear, Modificar, Eliminar
  - Quién (usuario)
  - Cuándo (fecha/hora)
  - Qué (tabla, ID registro)
  - Valores antes y después

#### RF-030: No Permitir Eliminar Auditoría
- Auditoría es inmutable
- Datos históricos nunca se borran
- Cumple con regulaciones

#### RF-031: Verificar Integridad
- El sistema debe analizar BD:
  - Tablas sin PK
  - Referencias foráneas inválidas
  - Datos inconsistentes
  - Stock negativo
  - Montos negativos

#### RF-032: Generar Reportes de Auditoría
- Filtrable por: Fecha, usuario, módulo, acción
- Exportable a PDF/Excel
- Incluir valores antes/después

### MÓDULO DE SEGURIDAD

#### RF-033: Autenticación con Usuario/Contraseña
- El sistema debe verificar credenciales
- Hash seguro (PBKDF2)
- Timeout de sesión (30 minutos)
- Logout obligatorio

#### RF-034: Implementar Roles
- El sistema debe soportar múltiples roles
- Predefinidos: Administrador, Director, Contador, Entrenador, Secretaría
- Personalizables

#### RF-035: Implementar Permisos Granulares
- Cada role tiene permisos específicos
- Ejemplo:
  - Administrador: Todo
  - Contador: Solo finanzas
  - Entrenador: Solo deportivo
  - Secretaría: Solo académico

#### RF-036: Protección CSRF
- El sistema debe incluir tokens CSRF
- Validar en cada POST/DELETE

#### RF-037: Cambiar Contraseña
- Usuario puede cambiar su contraseña
- Requerir contraseña actual
- Nueva contraseña mínimo 8 caracteres

### MÓDULO DE RESPALDOS

#### RF-038: Crear Respaldo Automático
- El sistema debe crear backup diariamente a las 23:00
- Formato: ZIP comprimido
- Ubicación: /instance/backups/
- Nombrado: academia_auto_YYYYMMDD_HHMMSS.db

#### RF-039: Crear Respaldo Pre-Migración
- Antes de cualquier migración
- Automático y obligatorio
- Almacenar con etiqueta de migración

#### RF-040: Restaurar Desde Respaldo
- El sistema debe permitir seleccionar fecha
- Haz clic "Restaurar"
- Valida integridad del respaldo
- Revierte a esa fecha
- Audita la restauración

#### RF-041: Verificar Integridad de Respaldo
- Al restaurar, verificar:
  - Archivo completo
  - Base de datos válida
  - Tablas presentes
  - No está corrupto

---

## 📊 REQUISITOS NO FUNCIONALES

### RNF-001: Operación y Disponibilidad en la Nube (SaaS)
- La plataforma opera 100% en la nube bajo modelo SaaS
- Acceso universal 24/7 los 365 días del año
- Cero instalación local ni requerimientos de servidores propios
- Copias de seguridad automáticas gestionadas en la nube

### RNF-002: Compatibilidad Multi-Dispositivo
- Compatible con cualquier sistema: Windows, macOS, Linux, Android, iOS
- Compatible con navegadores modernos: Chrome, Safari, Edge, Firefox
- Adaptabilidad total a pantallas de PC, tablet y celular

### RNF-003: Rendimiento
- Tiempo respuesta < 2 segundos (operaciones típicas)
- Sistema soporta hasta 50 usuarios simultáneos
- Base de datos < 1000 alumnos: sin degradación

### RNF-004: Escalabilidad
- Estructura permite crecer:
  - Más usuarios
  - Más datos
  - Migraciones futuras a PostgreSQL

### RNF-005: Disponibilidad
- Sistema disponible 99.9% del tiempo
- Recuperación ante desastres < 1 hora
- Respaldos redundantes

### RNF-006: Seguridad de Datos
- Contraseñas hasheadas con PBKDF2
- Acceso controlado por roles
- Auditoría de operaciones sensibles
- Sin datos sensibles en logs

### RNF-007: Integridad de Datos
- ACID compliance
- Transacciones atómicas
- Sin datos huérfanos
- Validaciones en aplicación + BD

### RNF-008: Validación de Datos
- Todos los campos validados
- Tipos de datos verificados
- Rangos validados (ej: edad > 0)
- Datos duplicados prevenidos

### RNF-009: Auditoría y Cumplimiento
- Toda operación registrada
- Quién, cuándo, qué, cómo
- No hay eliminación de auditoría
- Cumple normativas locales

### RNF-010: Usabilidad
- Interfaz intuitiva
- Menos de 3 clics para operación típica
- Mensajes de error claros
- Instrucciones inline

### RNF-011: Mantenibilidad
- Código limpio (PEP 8)
- Documentación completa
- Pruebas automáticas (85%+ cobertura)
- Estructura modular

### RNF-012: Portabilidad
- Datos portables (BD SQLite)
- Respaldos en múltiples formatos
- Migración a otros sistemas posible

---

## ✅ MATRIZ DE TRAZABILIDAD

| Req | Módulo | Implementado | Probado | Estado |
|-----|--------|--------------|---------|--------|
| RF-001 | Académico | ✅ | ✅ | Listo |
| RF-002 | Académico | ✅ | ✅ | Listo |
| RF-013 | Financiero | ✅ | ✅ | Listo |
| RF-014 | Financiero | ✅ | ✅ | Listo |
| ... | ... | ... | ... | ... |

**Estado General:** ✅ 100% de requisitos implementados y probados

---

*Documento de Requisitos v1.0.0*
