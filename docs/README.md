# README.md
# Sistema de Gestión de Academia Deportiva v1.0.0

![Status](https://img.shields.io/badge/Status-Production-green)
![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![License](https://img.shields.io/badge/License-Proprietary-red)
![Tests](https://img.shields.io/badge/Tests-126%2F126-green)

---

## 📋 Descripción

Sistema integral de gestión para academias deportivas que automatiza:
- ✅ Administración de alumnos y tutores
- ✅ Organización de campeonatos y partidos
- ✅ Control de pagos y obligaciones
- ✅ Gestión de inventario y ventas
- ✅ Auditoría completa de operaciones
- ✅ Respaldos automáticos

**Diseñado específicamente para academias deportivas en Bolivia.**

---

## 🚀 Características Principales

### Módulo Académico
- Gestión de 2,847+ registros de alumnos
- Categorías automáticas por edad
- Historiales y fichas en PDF
- Gestión de tutores

### Módulo Deportivo
- Campeonatos (Liga, Eliminación, Manual)
- Generación automática de fixtures
- Tabla de posiciones en tiempo real
- Registro de partidos y asistencia

### Módulo Financiero
- Pago de mensualidades
- Pagos parciales
- Generación de recibos
- Gestión de caja diaria

### Módulo de Auditoría
- Log de 162+ eventos auditados
- Trazabilidad completa
- Verificación de integridad
- Recuperación ante desastres

---

## 💻 Tecnologías

- **Backend:** Python 3.9+ con Flask
- **Base de Datos:** SQLite3 (0.93 MB)
- **ORM:** SQLAlchemy
- **Frontend:** HTML5, CSS3, Bootstrap5
- **Servidor:** Waitress
- **Respaldos:** ZIP comprimido
- **Reportes:** PDF (ReportLab) + Excel (openpyxl)

---

## 📦 Instalación

### Requisitos
- Windows 10/11 64 bits
- 500 MB espacio disco
- Navegador moderno (Chrome, Firefox, Edge)

### Pasos

1. **Descargar instalador**
   ```
   GestionAcademiaDeportiva_Setup_v1.0.0.exe
   ```

2. **Ejecutar**
   ```
   Doble clic en el archivo
   Seguir el asistente de instalación
   ```

3. **Configurar**
   ```
   Crear usuario administrador
   Acceder al sistema
   Cambiar contraseña (recomendado)
   ```

Ver **Manual_Instalacion.md** para detalles completos.

---

## 📖 Documentación

| Documento | Propósito |
|-----------|-----------|
| **01_DOCUMENTO_GENERAL.md** | Visión general del proyecto |
| **02_MANUAL_USUARIO.md** | Guía paso a paso para usuarios |
| **03_MANUAL_INSTALACION.md** | Instalación y configuración |
| **04_REQUISITOS.md** | Especificación de requisitos |
| **05_CASOS_USO.md** | Flujos de negocio |
| **06_PLAN_PRUEBAS.md** | Resultados de testing (126/126 ✅) |
| **07_MANUAL_BACKUP.md** | Respaldos y recuperación |
| **CHANGELOG.md** | Historial de versiones |

---

## 🧪 Pruebas

```
✅ 126 Pruebas Automáticas
✅ Integridad de BD: PERFECTA
✅ Seguridad: IMPLEMENTADA
✅ Rendimiento: OPTIMIZADO
✅ 85%+ Cobertura de Código
```

Ver **Plan_Pruebas.md** para detalles.

---

## 📊 Estadísticas del Proyecto

- **Versión:** 1.0.0
- **Líneas de Código:** 25,000+
- **Módulos:** 14
- **Tablas BD:** 57
- **Modelos:** 52 clases
- **Usuarios Soportados:** Hasta 50 simultáneos
- **Base de Datos:** 0.93 MB (2,847 registros)
- **Respaldos Disponibles:** 58

---

## 🔐 Seguridad

- ✅ Autenticación usuario/contraseña
- ✅ Roles y permisos granulares
- ✅ CSRF Protection
- ✅ SQL Injection Prevention
- ✅ XSS Prevention
- ✅ Auditoría inmutable
- ✅ Hash PBKDF2

---

## 💾 Respaldos

- ✅ Automáticos diarios
- ✅ Pre-migración obligatorio
- ✅ 58 respaldos disponibles
- ✅ Verificación de integridad
- ✅ Restauración validada

Ver **Manual_Backup.md** para procedimientos.

---

## ⚙️ Configuración

### Ubicación de Datos

```
C:\ProgramData\GestionAcademiaDeportiva\
├── academia.db          (Base de datos)
├── backups/             (Respaldos)
├── uploads/             (Fotos)
├── logs/                (Registros)
└── comprobantes/        (PDFs)
```

### Cambiar Ubicación de Datos

Antes de instalar:
```
setx ACADEMIA_DATA_DIR "D:\MisAcademias"
```

---

## 🚀 Uso Rápido

### Iniciar Sesión
1. Abrir navegador
2. Ingresar usuario y contraseña
3. Hacer clic en "Iniciar sesión"

### Crear Alumno
1. Ir a **Alumnos** → **Nuevo alumno**
2. Llenar datos
3. Hacer clic en **"Guardar"**

### Registrar Pago
1. Ir a **Pagos** → **Nuevo pago**
2. Seleccionar alumno
3. Ingresar monto
4. Hacer clic en **"Registrar"**

Ver **Manual_Usuario.md** para más funciones.

---

## 🐛 Solución de Problemas

### No puedo conectar
- Reinicia la computadora
- Verifica que el navegador esté actualizado
- Contacta soporte

### Base de datos corrupta
- Ir a **Administración** → **Integridad**
- Hacer clic en **[Reparar]**
- Si no funciona, restaurar desde respaldo

### Olvidé mi contraseña
- Contacta al administrador
- Te proporcionará acceso temporal

Ver **Manual_Instalacion.md** para más detalles.

---

## 📞 Soporte

**Para consultas técnicas:**
- 📧 Email: soporte@academia.com
- 📞 Teléfono: [Número de contacto]
- 🕐 Horario: Lunes-Viernes 09:00-17:00

---

## 📄 Licencia

Software propietario. Ver **LICENSE.txt** para términos completos.

---

## 🎯 Roadmap Futuro

- [ ] App móvil
- [ ] Integración bancaria
- [ ] Sincronización en tiempo real
- [ ] Soporte Linux/MacOS
- [ ] PostgreSQL como opción
- [ ] Dashboards BI

---

## 👨‍💼 Información de Versión

- **Versión:** 1.0.0
- **Fecha de Lanzamiento:** 16 de Agosto de 2026
- **Estado:** Listo para Producción ✅
- **Soporte:** 24 meses desde lanzamiento

---

## ✅ Checklist de Implementación

- [x] Módulo Académico completo
- [x] Módulo Deportivo completo
- [x] Módulo Financiero completo
- [x] Módulo de Inventario completo
- [x] Sistema de Seguridad
- [x] Sistema de Auditoría
- [x] Respaldos automáticos
- [x] 126 pruebas automáticas (100% pass)
- [x] Documentación completa
- [x] Instalador empaquetado
- [x] Listo para producción

---

**© 2026 Sistema Gestión Academia Deportiva**  
*Todos los derechos reservados*
