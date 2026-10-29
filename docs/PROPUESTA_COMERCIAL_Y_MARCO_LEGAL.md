# PROPUESTA COMERCIAL, TÉRMINOS DEL SERVICIO Y MARCO DE PROTECCIÓN DE DATOS
### Sistema de Gestión Integral para Academias Deportivas
**Planes de Suscripción, Políticas de Privacidad, Stack Tecnológico y Contrato Marco de Adhesión**  
*Edición Oficial — Estado Plurinacional de Bolivia (2026)*

---

## 1. Introducción y Propuesta de Valor

El presente documento constituye la **Propuesta Comercial Oficial, Términos de Prestación de Servicio de Software como Servicio (SaaS) y Políticas de Seguridad y Privacidad de Datos** que regulan la relación entre el **PROVEEDOR TECNOLÓGICO** (en adelante, el *Proveedor*) y la **ACADEMIA O CLUB DEPORTIVO** (en adelante, el *Cliente* o la *Academia*).

### Misión del Sistema
Nuestra plataforma está concebida exclusivamente para resolver los problemas críticos de administración deportiva en Bolivia:
1. **Control de Cobranza y Cero Evasión:** Elimina las mensualidades olvidadas o no cobradas mediante semaforización en tiempo real (*Vigente*, *Próximo a vencer*, *Vencido*) y cálculo automatizado de continuidad.
2. **Llamada de Asistencia Rápida en Cancha:** Interfaz táctil de alto contraste diseñada para profesores y entrenadores que permite pasar lista por categoría en menos de 30 segundos desde cualquier teléfono móvil.
3. **Caja Diaria y Arqueo Transparente:** Conciliación estricta entre pagos en efectivo y transferencias QR, con cierre diario inmutable y control de diferencias.
4. **Ficha Deportiva y Médica Integral:** Historial de habilitación a torneos, categorías, equipos, posiciones y control de edad con alerta de cambio de categoría.

---

## 2. Estructura de Planes y Tarifas Mensuales (en Bolivianos - Bs)

Los planes están escalonados para acompañar el crecimiento orgánico de la institución deportiva, garantizando costos predecibles, en moneda nacional y sin cobros sorpresa por comisiones ni transacciones:

| Plan Comercial | Tarifa Mensual | Capacidad Alumnos Activos | Perfil Institucional / Alcance Principal |
| :--- | :---: | :---: | :--- |
| **Plan Formativo** | **150 Bs / mes** | Hasta 60 alumnos | Escuelas formativas de barrio o proyectos en etapa inicial. Módulo esencial de registro, asistencia y cobro de mensualidades. |
| **Plan Pro (Estándar)** <br>*(Más Recomendado)* | **200 Bs / mes** | Hasta 120 alumnos | Academias en consolidación con múltiples turnos y profesores. Incluye caja diaria, arqueos, tienda de uniformes y respaldos en la nube. |
| **Plan Élite** | **250 Bs / mes** | **Alumnos ilimitados** | Clubes competitivos, múltiples categorías y alta rotación. Soporte 24/7 prioritario, multiusuario ilimitado y personalización visual. |

---

### Detalle de Cobertura por Plan

#### A. Plan Formativo (150 Bs / mes)
* **Capacidad:** Hasta 60 deportistas activos en el padrón.
* **Módulos incluidos:**
  * Padrón general de alumnos con código único interno (`ALU-XXXXXX`).
  * Asignación por categorías de edad y turnos (Mañana, Tarde, Noche).
  * Control de pagos de mensualidad con emisión de recibos digitales en PDF.
  * Toma de asistencia por categoría con selector rápido.
  * Historial básico del alumno y carnet digital descargable.
* **Soporte:** Asistencia técnica vía WhatsApp en horario laboral (Lunes a Viernes, 08:30 a 18:30).

#### B. Plan Pro — Estándar (200 Bs / mes) · *Plan Más Popular*
* **Capacidad:** Hasta 120 deportistas activos.
* **Módulos incluidos (todo lo del Plan Formativo más):**
  * **Módulo de Tesorería y Caja Diaria:** Apertura, control de entradas/salidas, arqueo de efectivo vs. QR y cierre de caja.
  * **Tienda e Inventario:** Control de stock de indumentaria deportiva, venta de uniformes asociada a la ficha del alumno y compras a proveedores.
  * **Gestión de Entrenadores y Personal:** Asignación de profesores a horarios y control de solapamiento de canchas.
  * **Subida Segura de Fotografías:** Procesamiento y saneamiento automático de fotos de alumnos con compresión y protección antimalware.
  * **Convocatorias Oficiales:** Generación de listas de citación para partidos con botón directo para compartir vía WhatsApp con padres de familia.
* **Soporte:** Soporte preferencial por WhatsApp y llamada telefónica de Lunes a Sábado.

#### C. Plan Élite (250 Bs / mes)
* **Capacidad:** **Alumnos ilimitados** (sin restricción de padrón).
* **Módulos incluidos (todo lo de los planes anteriores más):**
  * **Módulo Completo de Campeonatos y Torneos:** Fixture automatizado, cálculo de tablas de posiciones en vivo, fases de grupos y eliminatorias directas.
  * **Cuentas de Usuario Ilimitadas:** Accesos independientes para directores, coordinadores, profesores y personal de caja con permisos granulares.
  * **Personalización de Marca:** Configuración de escudo/logo institucional y colores corporativos de la academia en toda la plataforma y recibos.
  * **Respaldos Automatizados Diarios:** Copias de seguridad automáticas en la nube y herramienta de descarga de respaldo completo con un solo clic.
* **Soporte:** Soporte prioritario 24/7 para incidencias de servicio y atención de urgencia para eventos deportivos de fin de semana.

---

### Servicios Complementarios y Bonificaciones
1. **Puesta en Marcha Inicial (Setup Fee):**
   * Pago único de **150 a 200 Bs** (bonificable en contrataciones anuales).
   * Incluye: Configuración de marca (logo y colores), configuración de categorías y canchas, importación masiva del padrón de alumnos desde archivo Excel previo y capacitación guiada de 60 minutos al personal designado.
2. **Bonificación por Suscripción Anual:**
   * **Modalidad 10 = 12:** El cliente que abone 10 meses por adelantado recibe **12 meses completos de servicio** (2 meses de regalo).
     * Plan Formativo Anual: **1.500 Bs** *(ahorro de 300 Bs)*.
     * Plan Pro Anual: **2.000 Bs** *(ahorro de 400 Bs)*.
     * Plan Élite Anual: **2.500 Bs** *(ahorro de 500 Bs)*.

---

## 3. Stack Tecnológico y Arquitectura de Ingeniería

El sistema está construido siguiendo estándares modernos de desarrollo de software empresarial, priorizando velocidad, estabilidad y seguridad operativa:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CAPA 1: CLIENTE / FRONTEND                      │
│   HTML5 Semántico · CSS3 Vanilla (Obsidian Theme) · Bootstrap 5.3     │
│   HTMX (Renderizado Parcial Asíncrono) · JavaScript Vainilla Blindado  │
├────────────────────────────────────────────────────────────────────────┤
│                        CAPA 2: SERVIDOR / BACKEND                      │
│   Python 3.11 · Flask Modular (Blueprints de Dominio Aislados)         │
│   Gunicorn WSGI (Producción Linux) / Waitress WSGI (Producción Windows)│
│   Werkzeug Security (Scrypt Password Hashing) · CSRF Protection        │
├────────────────────────────────────────────────────────────────────────┤
│                     CAPA 3: PERSISTENCIA Y MOTOR DE BD                 │
│   PostgreSQL 15+ (Nube Supabase) / SQLite 3 WAL (Local Offline)        │
│   SQLAlchemy 2.0 ORM · Foreign Keys Estrictas · Constraints CHECK      │
├────────────────────────────────────────────────────────────────────────┤
│                  CAPA 4: PROCESAMIENTO MULTIMEDIA Y REPORTES           │
│   Pillow Engine (Sanitización de Imágenes) · ReportLab (PDFs Oficiales)│
│   OpenPyXL Engine (Exportación de Libros Financieros y Padrón Excel)   │
└────────────────────────────────────────────────────────────────────────┘
```

* **Lenguaje y Lógica de Negocio:** Python 3.11 estructurado en micro-módulos desacoplados (Alumnos, Pagos, Deporte, Agenda, Seguridad, Configuración).
* **Motor de Base de Datos:** PostgreSQL en producción en la nube (con soporte alternativo SQLite en modo WAL para academias que operan 100% offline sin internet).
* **Integridad Transaccional:** Cada operación que involucre dinero, inventario o cambios de estado opera bajo transacciones atómicas (`ACID`). Si un solo paso falla, se revierte toda la operación (`rollback`), garantizando que la base de datos jamás quede en estado inconsistente.
* **Generación Documental:** Todos los recibos, estados de cuenta, carnets y listas de convocatoria se renderizan dinámicamente en formato PDF vectorial nativo (ReportLab) e informes en hojas de cálculo Microsoft Excel (OpenPyXL).

---

## 4. Cláusulas de Protección Legal y Manejo Seguro de la Información

Para proteger jurídicamente a ambas partes y establecer con total claridad el alcance y la responsabilidad en el manejo de datos (especialmente de menores de edad y transacciones económicas), se fijan las siguientes condiciones:

### Cláusula 4.1: Delimitación de Roles y Propiedad de los Datos
1. **Propiedad Exclusiva:** La Academia Cliente es la **única y exclusiva propietaria** de toda la información ingresada a la plataforma, incluyendo nombres, cédulas de identidad, números telefónicos, direcciones, imágenes de los menores, datos de tutores y registros contables.
2. **Rol del Proveedor:** El Proveedor actúa exclusivamente en calidad de **Encargado del Tratamiento Tecnológico y Custodio Digital**. Bajo ninguna circunstancia el Proveedor podrá:
   * Vender, ceder, transferir, comercializar o compartir información del Cliente con terceras empresas, patrocinadores o agencias de publicidad.
   * Utilizar los números de contacto o correos de los tutores para fines distintos al estricto soporte del sistema.
3. **Rol del Cliente (Responsable del Fichero):** La Academia Cliente es la única responsable legal de contar con la autorización correspondiente de los padres de familia o tutores legales para recolectar sus datos personales y fotografías con fines de inscripción deportiva, conforme a la normativa vigente en el Estado Plurinacional de Bolivia.

### Cláusula 4.2: Exención de Responsabilidad por Fuga de Credenciales del Usuario
1. El sistema proporciona mecanismos robustos de autenticación (contraseñas encriptadas mediante algoritmos criptográficos irreversibles `scrypt`).
2. **Deber de Custodia del Cliente:** El personal de la Academia es plenamente responsable de mantener en estricta reserva sus usuarios y contraseñas.
3. **Exoneración:** El Proveedor no asume responsabilidad alguna por accesos indebidos, alteraciones de registros o filtraciones de datos derivadas de:
   * Contraseñas débiles, compartidas o anotadas en lugares públicos.
   * Sesiones dejadas abiertas en computadoras compartidas, cibercafés o dispositivos móviles sin bloqueo.
   * Dispositivos de la academia infectados por virus, troyanos o keyloggers ajenos al servidor de la plataforma.

### Cláusula 4.3: Privacidad y Protección Específica de Menores (Saneamiento de Metadatos)
1. **Destrucción de Metadatos EXIF / GPS:** Cada vez que la academia sube una fotografía de un alumno, el motor interno de procesamiento ([alumnos.py](file:///c:/Users/Usuario/.gemini/antigravity-ide/scratch/academia-futbol-marcelo/app/routes/alumnos.py)) analiza el archivo con la librería `Pillow`, **elimina por completo los datos de geolocalización GPS** y metadatos del dispositivo que pudieran revelar la ubicación de la vivienda o escuela del menor.
2. **Neutralización Antimalware:** La imagen se recompila pixel a pixel en un formato seguro (`JPEG`/`PNG`/`WEBP`) con nombre criptográfico aleatorio (`UUIDv4`), impidiendo la ejecución de archivos maliciosos camuflados.
3. **Acceso Privado a Fotografías:** Las fotografías no son accesibles mediante URLs públicas de internet; requieren autenticación y sesión activa en la plataforma.

### Cláusula 4.4: Respaldo, Portabilidad y Retención de Datos
1. **Derecho a la Portabilidad:** La Academia puede, en cualquier momento y sin costo alguno, descargar un **Respaldo Completo de su Base de Datos** desde el panel de administración, así como exportar padrones y estados de cuenta en formatos abiertos (`Excel`, `PDF`, `CSV`).
2. **Política de Suspensión por Falta de Pago:**
   * La suscripción debe cancelarse dentro de los primeros **5 días calendario** de cada mes.
   * En caso de mora, se otorga un **periodo de gracia de 5 días adicionales** con acceso de solo lectura.
   * Si tras el periodo de gracia no se regulariza el pago, el acceso al sistema se suspende temporalmente.
3. **Custodia de Resguardo (30 Días):** El Proveedor custodiará de forma íntegra e intacta la base de datos de la academia durante **30 días calendario** posteriores a la suspensión. Si el Cliente regulariza su suscripción dentro de este plazo, el servicio se reactiva de inmediato con toda su información intacta.
4. **Borrado Seguro Posterior:** Transcurridos los 30 días de custodia sin regularización ni solicitud formal de exportación, el Proveedor procederá al archivado seguro o eliminación definitiva de los datos del servidor para no acumular información sensible en desuso.

### Cláusula 4.5: Acuerdo de Nivel de Servicio (SLA) y Fuerza Mayor
1. **Disponibilidad Objetivo:** El Proveedor compromete sus mejores esfuerzos técnicos para mantener una disponibilidad de servicio del **99.0%** mensual en la infraestructura en la nube.
2. **Mantenimientos Programados:** Cualquier actualización crítica que requiera reinicio o corte de servicio será notificada con al menos **24 horas de anticipación** y ejecutada en horarios nocturnos (entre las 23:00 y las 05:00, hora de Bolivia).
3. **Límites de Responsabilidad / Fuerza Mayor:** El Proveedor queda exonerado de responsabilidad por interrupciones temporales causadas por:
   * Fallas masivas de proveedores globales de nube (ej. incidentes generales en AWS, Render o Cloudflare).
   * Cortes de suministro eléctrico o caídas del servicio de internet de las empresas proveedoras de telecomunicaciones locales (Entel, Tigo, AXS, etc.).
   * Bloqueos, fallas de hardware en los dispositivos propios del Cliente o desastres naturales.

---

## 5. Derechos y Obligaciones de las Partes

### A. Obligaciones del Proveedor
1. Proveer la plataforma digital operativa, libre de errores críticos que impidan el registro de alumnos o el cobro de mensualidades.
2. Aplicar parches de seguridad, optimizaciones de velocidad y mejoras correctivas continuas sin costo adicional.
3. Atender las consultas técnicas y solicitudes de soporte canalizadas por el responsable designado por la academia, en los tiempos establecidos según el plan contratado.
4. Mantener la estricta reserva profesional sobre los montos de recaudación, ingresos y operaciones de la academia.

### B. Obligaciones de la Academia (Cliente)
1. Abonar puntualmente el monto mensual o anual convenido para mantener la vigencia del servicio.
2. Utilizar el sistema con fines estrictamente lícitos y vinculados a la administración de su institución deportiva.
3. Asignar las cuentas de usuario de acuerdo con el rol real del personal (ej. no otorgar permisos de Administrador a personal auxiliar que solo deba pasar lista).
4. Comunicar inmediatamente al Proveedor cualquier anomalía o comportamiento imprevisto detectado en la plataforma.

### C. Propiedad Intelectual del Software
El Cliente reconoce que la contratación del servicio le otorga únicamente una **Licencia de Uso Temporal (SaaS)**. El código fuente, la arquitectura, el diseño visual, la base lógica, algoritmos y documentación del sistema son y seguirán siendo de **propiedad intelectual exclusiva del Proveedor**, no teniendo el Cliente derecho a revender, copiar, descompilar, realizar ingeniería inversa ni sublicenciar la plataforma a terceros.

---

## 6. Procedimiento de Contratación y Formas de Pago

1. **Aceptación de Términos:** La suscripción entra en vigencia a partir del pago del primer periodo o del abono de la tarifa de puesta en marcha.
2. **Moneda y Canales de Pago:** Todos los pagos se liquidan en **Bolivianos (Bs)** mediante:
   * Transferencia bancaria directa / Interbancaria (ACH).
   * Cobro oficial mediante código **QR Simple** (Banco Unión, BCP, BNB, Banco Mercantil Santa Cruz o cualquier entidad financiera nacional).
3. **Facturación / Comprobante:** Se emitirá el correspondiente comprobante digital de recepción de fondos o documento equivalente por la prestación del servicio tecnológico.

---

## 7. Firma y Conformidad de Adhesión

Para constancia de la aceptación mutua de los términos técnicos, comerciales y de privacidad expuestos:

<br><br>

```
_________________________________________            _________________________________________
        POR EL PROVEEDOR TECNOLÓGICO                         POR LA ACADEMIA DEPORTIVA
Nombre: _________________________________            Nombre Director/a: ______________________
CI / NIT: _______________________________            CI: _____________________________________
Cargo: Dirección Técnica de Software                 Institución: ____________________________
Fecha: _____ / _____ / 2026                          Fecha: _____ / _____ / 2026
```
