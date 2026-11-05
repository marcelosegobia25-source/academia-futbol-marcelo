# MANUAL DE BACKUP Y RECUPERACIÓN
## Sistema de Gestión de Academia Deportiva

**Versión:** 1.0.0  
**Importancia:** CRÍTICA

---

## 🔴 LEER PRIMERO

**IMPORTANTE:** Este manual contiene información CRÍTICA para la operación del sistema.

El sistema Academia Deportiva ha sido diseñado con redundancia de respaldos para garantizar que:
- ✅ Nunca pierda datos por accidente
- ✅ Pueda recuperarse rápidamente ante desastres
- ✅ Tenga historial completo de cambios

---

## 1. SISTEMA DE RESPALDOS AUTOMÁTICOS

### 1.1 ¿Qué son los respaldos automáticos?

El sistema crea una copia completa de la base de datos **automáticamente** cada día.

```
Horario:       Todos los días a las 23:00 (11 PM)
Tipo:          Backup completo (ZIP comprimido)
Ubicación:     C:\ProgramData\GestionAcademiaDeportiva\backups\
Retención:     Últimos 60 días (~60 respaldos)
Tamaño:        ~1 MB cada uno
Validación:    Integridad verificada automáticamente
```

### 1.2 Estructura de un respaldo

```
academia_auto_20260816_230000.db
│
├── Base de datos completa
├── Todas las tablas (57)
├── Todos los registros (2,847+)
├── Índices y relaciones
└── Configuración del sistema
```

**Nombre del archivo:** `academia_auto_YYYYMMDD_HHMMSS.db`
- YYYY = Año (2026)
- MM = Mes (08)
- DD = Día (16)
- HH = Hora (23)
- MM = Minuto (00)
- SS = Segundo (00)

---

## 2. VER RESPALDOS DISPONIBLES

### Paso a paso:

1. Abre el navegador
2. Accede al sistema
3. Ve a **Administración** → **Respaldos**
4. Verás una tabla con:
   - Fecha y hora del respaldo
   - Tamaño del archivo
   - Opción "Descargar"
   - Opción "Restaurar"

### Ejemplo:

```
Fecha/Hora              | Tamaño   | Acciones
-----------------------|----------|-------------------
2026-08-16 23:00:00     | 0.93 MB  | [Descargar] [Restaurar]
2026-08-15 23:00:00     | 0.93 MB  | [Descargar] [Restaurar]
2026-08-14 23:00:00     | 0.93 MB  | [Descargar] [Restaurar]
2026-08-13 23:00:00     | 0.93 MB  | [Descargar] [Restaurar]
...
```

---

## 3. CREAR RESPALDO MANUAL

A veces necesitas crear un respaldo manual **antes** de hacer cambios importantes.

### Paso a paso:

1. Ve a **Administración** → **Respaldos**
2. Haz clic en **[Crear respaldo ahora]**
3. Sistema muestra:
   ```
   Creando respaldo...
   ████████████████████ 100%
   ✓ Respaldo creado: academia_manual_20260816_143000.db
   ```
4. El respaldo se agrega a la lista

**¿Cuándo crear manual?**
- Antes de importar datos masivos
- Antes de cambios importantes de configuración
- Antes de actualizar el sistema
- Antes de entrenar a nuevos usuarios

---

## 4. DESCARGAR UN RESPALDO

Si quieres tener una copia en USB o nube:

### Paso a paso:

1. Ve a **Administración** → **Respaldos**
2. Busca la fecha que quieres
3. Haz clic en **[Descargar]**
4. Se descarga el archivo `academia_auto_YYYYMMDD_HHMMSS.db`
5. Guarda en:
   - USB externo
   - Carpeta compartida en red
   - Servicio de nube (OneDrive, Google Drive)

**Recomendación:** Descarga respaldos mensuales a USB como medida de seguridad extra.

---

## 5. RESTAURAR DESDE UN RESPALDO

### ⚠️ ANTES DE RESTAURAR - LEE ESTO

Restaurar significa:
- ✅ Volver a una fecha anterior
- ✅ Recuperar datos perdidos
- ❌ **PIERDES TODOS LOS DATOS DESPUÉS DE ESA FECHA**

**Ejemplo:** Si restauras desde 2026-08-10, pierdes todo lo del 11, 12, 13, etc.

### Paso a paso:

1. Ve a **Administración** → **Respaldos**
2. **Primero:** Crea un respaldo de seguridad del estado actual:
   - Haz clic en **[Crear respaldo ahora]**
   - Espera a que termine
3. Busca la fecha que quieres restaurar
4. Haz clic en **[Restaurar]**
5. Sistema pregunta:
   ```
   ⚠️ ADVERTENCIA
   Se restaurará la BD desde 2026-08-10 23:00
   Todos los datos posteriores se perderán.
   ¿Está seguro?
   
   [Cancelar]  [Restaurar]
   ```
6. Haz clic en **[Restaurar]** para confirmar
7. Sistema:
   - Detiene la aplicación
   - Restaura archivos
   - Verifica integridad
   - Reinicia
   ```
   Restaurando base de datos...
   Verificando integridad...
   Reiniciando aplicación...
   ✓ Restauración completada
   ```
8. Sistema se reinicia automáticamente
9. Accede nuevamente con tu usuario/contraseña

### Después de restaurar:

1. Verifica que los datos sean correctos
2. Ve a **Administración** → **Integridad**
3. Verifica que no hay errores
4. Todos pueden volver a trabajar

---

## 6. RESTAURAR EN COMPUTADORA DIFERENTE

Si necesitas migrar a otra computadora:

### Paso a paso:

1. **En computadora origen:**
   - Ve a **Administración** → **Respaldos**
   - Descargar el respaldo deseado
   - Guardar en USB

2. **En computadora destino:**
   - Instalar el sistema (ver Manual de Instalación)
   - Crear usuario inicial
   - Ve a **Administración** → **Respaldos**
   - Haz clic en **[Restaurar desde archivo]**
   - Selecciona el archivo del USB
   - Sistema restaura los datos

---

## 7. PLAN DE RESPALDOS RECOMENDADO

Para máxima seguridad, implementa este plan:

### Diario
- ✅ Sistema crea automáticamente a las 23:00

### Semanal
- 📌 Cada viernes, descarga respaldo a USB
- Guarda en carpeta: "Respaldos Semanales"

### Mensual
- 📌 Primer día del mes, descarga respaldo
- Guarda en carpeta: "Respaldos Mensuales"
- Guarda en nube también

### Anual
- 📌 Fin de año, descarga respaldo
- Archivo histórico permanente

---

## 8. ALMACENAMIENTO SEGURO

### Dónde guardar respaldos

**LOCAL:**
- [ ] En la misma computadora (NO es suficiente)
- [ ] En USB externo (SÍ)
- [ ] En carpeta red (SÍ)

**NUBE:**
- [ ] Google Drive (SÍ)
- [ ] OneDrive (SÍ)
- [ ] Dropbox (SÍ)
- [ ] Servidor de la academia (SÍ)

**Recomendación:** 3 copias en locaciones diferentes
- Copia 1: Automática (en sistema)
- Copia 2: USB externo en la academia
- Copia 3: Nube o servidor remoto

---

## 9. QUESTA HACER SI ALGO SALIÓ MAL

### Síntoma: "Base de datos corrupta"

**¿Qué hacer?**

1. NO continúes usando el sistema
2. Contacta al administrador
3. Administrador ejecuta:
   - Ve a **Administración** → **Integridad**
   - Haz clic en **[Reparar]**
   - Si falla, restaura desde respaldo

### Síntoma: "Se borró información importante"

**¿Qué hacer?**

1. Determina aproximadamente cuándo se borró
2. Ve a **Administración** → **Respaldos**
3. Elige respaldo ANTERIOR a esa fecha
4. Restaura
5. (Pierdes cambios posteriores, pero recuperas lo borrado)

### Síntoma: "El sistema no inicia"

**¿Qué hacer?**

1. Intenta reiniciar la computadora
2. Si no inicia:
   - Restaura desde respaldo
   - Si no funciona, contacta soporte

---

## 10. PROCEDIMIENTOS CRÍTICOS

### Antes de actualizar el sistema

```
1. Crear respaldo manual
   → Administración → Respaldos → [Crear]
   
2. Descargar respaldo a USB
   → [Descargar]
   
3. Guardar en carpeta física
   → "C:\MisRespaldos\Actualización_2026-08-16.db"
   
4. Proceder con actualización
```

### Antes de importar datos masivos

```
1. Crear respaldo manual
2. Descargar a USB
3. Realizar importación
4. Verificar que los datos se vean bien
5. Si algo salió mal, restaurar
```

### Antes de cambios de configuración importante

```
1. Crear respaldo
2. Hacer cambios
3. Probar que funcione
4. Si falla, restaurar
```

---

## 11. RECUPERACIÓN ANTE DESASTRE

### Escenario: Computadora se daña completamente

**Procedimiento:**

1. Obtener computadora nueva
2. Instalar Windows
3. Instalar Sistema Academia Deportiva
4. Ir a **Administración** → **Respaldos**
5. Haz clic en **[Restaurar desde archivo]**
6. Selecciona respaldo guardado en USB/nube
7. Sistema restaura todos los datos
8. ✅ Sistema operativo nuevamente

**Tiempo estimado:** 30-45 minutos

---

## 12. CHECKLIST MENSUAL

Ejecuta esta lista una vez al mes:

```
☐ Verificar que respaldos se crean automáticamente
  → Ir a Administración → Respaldos
  → Verificar que hay respaldo de hoy

☐ Descargar respaldo mensual
  → Seleccionar respaldo
  → Haz clic [Descargar]
  → Guardar en carpeta segura

☐ Verificar integridad
  → Administración → Integridad
  → Verificar que todo sea "OK"

☐ Probar restauración (opcional pero recomendado)
  → Crear respaldo de seguridad primero
  → Restaurar respaldo anterior
  → Verificar que datos sean correctos
  → Restaurar respaldo actual

☐ Documentar
  → Anotar fecha y tamaño de respaldo
  → Registrar en log interno
```

---

## 13. PREGUNTAS FRECUENTES

**P: ¿Qué pasa si me olvido de crear respaldos?**
R: No hay problema. El sistema los crea automáticamente cada día. Solo asegúrate de descargarlos a USB para protección adicional.

**P: ¿Pierdo todos los datos si restauro?**
R: Solo pierdes los datos POSTERIORES a la fecha del respaldo. Los datos hasta esa fecha se recuperan.

**P: ¿Puedo restaurar parcialmente?**
R: No. La restauración es completa (toda la BD). Pero puedes restaurar una copia en otra computadora y copiar datos específicos.

**P: ¿Cuál es el tamaño de un respaldo?**
R: Aproximadamente 1 MB para 2,847 registros. Con 10,000 registros ~5 MB.

**P: ¿Por cuánto tiempo guardan respaldos?**
R: 60 días por defecto. Los más antiguos se eliminan automáticamente.

---

## Más Información

📧 Soporte: soporte@academia.com  
📞 Teléfono: [Número]  
📚 Documentación: DOCUMENTACION_ENTREGA/

---

*Manual de Backup v1.0.0*
