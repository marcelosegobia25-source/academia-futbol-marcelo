# MANUAL DE INSTALACIÓN
## Sistema de Gestión de Academia Deportiva

**Versión:** 1.0.0  
**Plataforma:** Windows 10/11 64 bits  
**Última Actualización:** 16 de Agosto de 2026

---

## 📋 TABLA DE CONTENIDOS

1. Requisitos del Sistema
2. Pre-Instalación
3. Proceso de Instalación
4. Configuración Inicial
5. Creación de Usuario Inicial
6. Verificación de Instalación
7. Ubicación de Archivos
8. Actualización del Sistema
9. Desinstalación
10. Troubleshooting

---

## 1. REQUISITOS DEL SISTEMA

### Hardware Mínimo Requerido

| Componente | Requisito | Recomendado |
|-----------|-----------|-------------|
| **Procesador** | Intel Core i3 | Intel Core i5 o mejor |
| **RAM** | 4 GB | 8 GB |
| **Almacenamiento** | 500 MB libres | 2 GB |
| **Pantalla** | 1024x768 px | 1366x768 px o mayor |
| **Conexión** | Opcional | 5 Mbps para soporte |

### Software Requerido

- **Sistema Operativo:** Windows 10 o Windows 11 (64 bits)
- **Navegador:** Chrome, Firefox, Edge (versión reciente)
- **.NET Framework:** Se instala automáticamente con el programa

**Nota:** No se requiere Internet para usar el sistema, pero se recomienda para:
- Soporte técnico remoto
- Descarga de actualizaciones
- Respaldo en nube (futuro)

### Permisos Requeridos

- Acceso de administrador para instalar
- Permiso de escritura en C:\ProgramData\
- Permiso para crear carpetas

---

## 2. PRE-INSTALACIÓN

### Paso 1: Verificar Espacio Disponible

1. Abre **Explorador de Archivos**
2. Haz clic derecho en **C:**
3. Selecciona **Propiedades**
4. Verifica que haya al menos **500 MB libres**

### Paso 2: Cerrar Programas

Cierra todos los programas, especialmente:
- Excel
- Word
- Otros navegadores
- Antivirus (temporalmente)

### Paso 3: Desactivar Antivirus

Si es necesario:

1. Abre tu antivirus
2. Desactívalo temporalmente
3. Después de instalar, actívalo nuevamente

**Nota:** Es normal que el antivirus quiera bloquear la instalación. Permite que continúe.

---

## 3. PROCESO DE INSTALACIÓN

### Paso 1: Obtener el Instalador

Recibe el archivo:
```
GestionAcademiaDeportiva_Setup_v1.0.0.exe
```

### Paso 2: Ejecutar el Instalador

1. Localiza el archivo descargado (generalmente en Descargas)
2. Haz doble clic en el archivo
3. Si Windows pregunta **"¿Permitir que este programa realice cambios?"**, haz clic en **Sí**

### Paso 3: Pantalla de Bienvenida

Verás la pantalla de Inno Setup:

```
┌─────────────────────────────────────┐
│ Gestor Instalador                   │
│                                     │
│ Bienvenido a la Instalación         │
│ Sistema Gestión Academia Deportiva  │
│                                     │
│ [Siguiente]                         │
└─────────────────────────────────────┘
```

Haz clic en **[Siguiente]**

### Paso 4: Aceptar Licencia

Lee la licencia y selecciona:
```
☑ Acepto los términos de la licencia
```

Luego haz clic en **[Siguiente]**

### Paso 5: Seleccionar Ubicación

Te mostrará la carpeta de instalación predeterminada:
```
C:\Program Files (x86)\GestionAcademiaDeportiva
```

**Recomendación:** Deja la ubicación por defecto.

Si deseas cambiarla:
1. Haz clic en **[Examinar]**
2. Selecciona una carpeta
3. Haz clic en **[Siguiente]**

### Paso 6: Seleccionar Componentes

```
☑ Programa principal (REQUERIDO)
☑ Acceso directo en escritorio
☑ Acceso rápido en menú inicio
```

Deja todas marcadas y haz clic en **[Siguiente]**

### Paso 7: Confirmación

Verás un resumen de la instalación:

```
Ubicación: C:\Program Files (x86)\GestionAcademiaDeportiva
Componentes: Programa, Accesos directos
Espacio requerido: 350 MB
```

Haz clic en **[Instalar]** para comenzar.

### Paso 8: Instalación en Progreso

Verás una barra de progreso. **Espera hasta que termine (2-5 minutos).**

```
[████████░░░░░░░░░░░░] 45%
```

### Paso 9: Instalación Completada

Cuando termine:

```
┌─────────────────────────────────────┐
│ Instalación Completada              │
│                                     │
│ ✓ Sistema instalado exitosamente    │
│                                     │
│ ☑ Ejecutar programa ahora           │
│                                     │
│ [Finalizar]                         │
└─────────────────────────────────────┘
```

Deja marcado **"Ejecutar programa ahora"** y haz clic en **[Finalizar]**

---

## 4. CONFIGURACIÓN INICIAL

### Primer Inicio

El programa se abrirá automáticamente. Verás:

```
┌─────────────────────────────────────┐
│ Gestión Academia Deportiva          │
│ Sistema iniciándose...              │
│                                     │
│ Inicializando base de datos...      │
│ Creando tablas...                   │
│ Cargando configuración...           │
│                                     │
│ ████████████████████ 100%           │
└─────────────────────────────────────┘
```

**Tiempo estimado:** 30-60 segundos.

**Nota:** Si ves mensajes de error, ver sección Troubleshooting.

### Configuración de Base de Datos

La aplicación automáticamente:
- ✅ Crea la base de datos
- ✅ Crea todas las tablas (57 tablas)
- ✅ Establece relaciones
- ✅ Crea índices
- ✅ Inicializa roles y permisos

---

## 5. CREACIÓN DE USUARIO INICIAL

### Primer Acceso

Al iniciar por primera vez, verás la pantalla de **Crear Usuario Inicial**:

```
┌─────────────────────────────────────┐
│ Crear Usuario Administrador         │
│                                     │
│ Usuario: [________________]         │
│ Contraseña: [________________]      │
│ Confirmar: [________________]       │
│                                     │
│ [Crear]  [Salir]                    │
└─────────────────────────────────────┘
```

### Datos para el Usuario Inicial

Rellena:

1. **Usuario:**
   - Mínimo 4 caracteres
   - Solo letras y números
   - Ejemplo: `admin` o `director2026`

2. **Contraseña:**
   - Mínimo 8 caracteres
   - Incluye MAYÚSCULA, minúscula, número
   - Ejemplo: `Admin123`

3. **Confirmar:**
   - Repite la misma contraseña

### Crear el Usuario

Haz clic en **[Crear]**

Sistema responderá:
```
✓ Usuario administrador creado exitosamente
Iniciando sesión...
```

---

## 6. VERIFICACIÓN DE INSTALACIÓN

### Verificar que todo está correcto

Después de crear el usuario, verás el **Panel Principal**.

**Comprueba que:**

1. ✅ El navegador abre
2. ✅ Ves el menú lateral izquierdo
3. ✅ Ves tu usuario en la esquina superior derecha
4. ✅ Puedes hacer clic en cada módulo

### Primera Vez: Cambiar Contraseña

Por seguridad, se recomienda cambiar la contraseña inicial:

1. Haz clic en tu **usuario** (arriba a la derecha)
2. Selecciona **Cambiar contraseña**
3. Ingresa la contraseña actual
4. Ingresa una nueva contraseña
5. Haz clic en **[Guardar]**

---

## 7. UBICACIÓN DE ARCHIVOS

### Dónde se guardan los datos

```
Windows (Ubicación automática):
C:\ProgramData\GestionAcademiaDeportiva\
├── academia.db              ← Base de datos principal
├── backups/                 ← Respaldos automáticos
│   ├── academia_auto_20260816.db
│   ├── academia_auto_20260815.db
│   └── ...
├── uploads/                 ← Fotos de alumnos
│   └── alumnos/
├── logs/                    ← Archivos de registro
│   ├── academia.log
│   └── server.log
├── comprobantes/            ← PDFs generados
└── Descargas/               ← Exportaciones Excel
```

### Acceder a los datos

**Para cambiar la ubicación de datos:**

1. Antes de instalar, abre **Símbolo del Sistema**
2. Ejecuta:
```
setx ACADEMIA_DATA_DIR "D:\MisAcademias"
```
3. Luego instala el programa
4. Los datos se guardarán en D:\MisAcademias

---

## 8. ACTUALIZACIÓN DEL SISTEMA

### Recibir Actualizaciones

Periódicamente recibirás nuevas versiones:
```
GestionAcademiaDeportiva_Setup_v1.1.0.exe
```

### Proceso de Actualización

1. **Crear Respaldo (IMPORTANTE):**
   - Ve a **Administración** → **Respaldos**
   - Haz clic en **[Crear respaldo]**
   - Espera a que termine

2. **Descargar Instalador:**
   - Obtén el nuevo ejecutable
   - Guarda en una carpeta

3. **Ejecutar Instalador:**
   - Haz doble clic en el nuevo archivo
   - Sigue los mismos pasos de instalación
   - Sistema detectará la versión anterior

4. **Aplicar Migraciones:**
   - Si hay cambios en la BD, se aplican automáticamente
   - Verás un mensaje:
   ```
   Actualizando base de datos...
   Aplicando migraciones...
   ✓ Actualización completada
   ```

5. **Verificar:**
   - Ve a **Administración** → **Integridad**
   - Verifica que todo está correcto

---

## 9. DESINSTALACIÓN

### Desinstalar el Programa

Si necesitas desinstalar:

1. Abre **Panel de Control**
2. Ve a **Programas** → **Programas y Características**
3. Busca **"Gestión Academia Deportiva"**
4. Haz clic en **[Desinstalar]**
5. Confirma la desinstalación

### Conservar los Datos

**IMPORTANTE:** La desinstalación NO borra los datos.

Los datos permanecen en:
```
C:\ProgramData\GestionAcademiaDeportiva\academia.db
```

Si instalas nuevamente, tus datos seguirán allí.

### Borrar Datos Completamente

Si quieres eliminar TODO incluyendo datos:

1. Desinstala el programa (ver arriba)
2. Abre **Explorador de Archivos**
3. Navega a: `C:\ProgramData\GestionAcademiaDeportiva\`
4. Selecciona TODO
5. Presiona **Suprimir**
6. Confirma

---

## 10. TROUBLESHOOTING

### Problema: "No se puede conectar a la base de datos"

**Causa:** La BD está corrupta o inaccesible.

**Solución:**

1. Ve a **Administración** → **Respaldos**
2. Selecciona un respaldo reciente
3. Haz clic en **[Restaurar]**
4. Confirma y espera

### Problema: "El sistema no inicia"

**Causa:** Puertos ocupados o conflicto de software.

**Solución:**

1. Reinicia la computadora
2. Desinstala y reinstala el programa
3. Si persiste, contacta soporte

### Problema: "Base de datos corrupta"

**Síntomas:**
- Errores al guardar
- Datos desaparecidos
- Consultas lentísimas

**Solución:**

1. Ve a **Administración** → **Integridad**
2. Sistema analiza y reporta problemas
3. Ejecuta **"Reparar integridad"**
4. Si no se puede reparar, restaura un respaldo

### Problema: "No tengo permisos"

Si ves mensajes de acceso denegado:

1. Ejecuta el programa como Administrador:
   - Clic derecho en el acceso directo
   - Selecciona **"Ejecutar como administrador"**

2. Si el problema persiste:
   - Cambia permisos de carpeta:
   - C:\ProgramData\GestionAcademiaDeportiva
   - Clic derecho → Propiedades → Seguridad
   - Asegúrate de tener permisos Lectura/Escritura

### Problema: "Incompatibilidad de navegador"

Si ves la pantalla en blanco o desalineada:

1. Intenta con otro navegador (Chrome, Firefox)
2. Limpia caché: Ctrl+Shift+Delete
3. Desactiva extensiones del navegador

### Problema: El antivirus bloquea la instalación

Es normal. Cuando veas la advertencia:

1. Haz clic en **"Permitir de todas formas"**
2. O **"Más información"** → **"Ejecutar de todas formas"**
3. La aplicación no contiene malware

---

## Información de Soporte

**Para problemas técnicos:**

📧 Email: soporte@academia.com  
📞 Teléfono: [Número]  
🕐 Horario: Lunes-Viernes 09:00-17:00

**Documentación adicional:**
- Manual de Usuario
- Manual Técnico
- Base de Datos de Ayuda

---

*Manual de Instalación v1.0.0 - Sistema Gestión Academia Deportiva*
