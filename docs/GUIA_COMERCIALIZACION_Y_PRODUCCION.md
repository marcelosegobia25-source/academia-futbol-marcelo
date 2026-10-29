# Guía Integral de Comercialización, Producción y Estrategia Multi-Cliente
### Sistema de Gestión para Academias Deportivas

Este documento recopila la estrategia técnica y comercial para mantener el sistema en producción, comercializarlo con múltiples academias, estructurar los precios y operar de forma segura con costo de infraestructura cero.

---

## 1. Infraestructura y Tiempo en Producción

### A. Entorno en la Nube Gratuita (Render Free + Supabase Free)

| Parámetro | Comportamiento | Impacto Operativo |
| :--- | :--- | :--- |
| **Vigencia del servicio** | **Indefinido / Permanente** | No es una versión de prueba de 14 o 30 días. Es gratuito permanentemente. |
| **Suspensión por inactividad (Render)** | Se apaga tras **15 minutos** sin visitas. | La primera persona que entra tras un receso espera **30 a 50 segundos** mientras el servidor despierta (cold start). Una vez despierto, responde de inmediato. |
| **Horas mensuales de cómputo** | **750 horas gratis / mes** por cuenta. | Un mes tiene 720–744 horas. Alcanza exactamente para **1 academia activa todo el mes** en esa cuenta. |
| **Regla de los 7 días (Supabase)** | Se pausa si pasa **7 días seguidos sin consultas**. | En recesos largos de vacaciones, si se pausa, no se pierde nada: basta ingresar a [supabase.com](https://supabase.com) y pulsar *"Restore project"*. Mientras se use 1 vez por semana, nunca se pausa. |
| **Archivos y fotos en disco** | El disco de Render Free es efímero. | Los datos de texto, cobros y alumnos (Supabase) son permanentes. Las fotos de perfil subidas se reinician si el contenedor se reconstruye. |

### B. Entorno en Producción Local (Computadora de la Academia)

* **Tiempo:** **Ilimitado de por vida ($0 de costo).**
* **Conexión:** Opera 100% sin internet, inmune a caídas de red o cortes de servicio.
* **Almacenamiento:** Base de datos (`instance/academia.db`), fotos y respaldos se guardan en el disco físico local.
* **Comando para servicio continuo:**
  ```powershell
  .venv\Scripts\python.exe serve.py
  ```
  *(Utiliza el servidor WSGI `Waitress`, diseñado para producción multihilo en Windows).*

### C. Opción Servidor Propio (VPS Económico - $4 a $5 USD/mes)

Si en el futuro deseas que múltiples academias funcionen en la nube 24/7 sin hibernación ni pausas:
* En proveedores como **Hetzner (€3.50/mes)** o **DigitalOcean ($4–$5 USD/mes)** puedes alojar **10 a 20 academias juntas** en un solo servidor pequeño.
* El costo es fijo y plano: pagas solo los $4 o $5 al mes en total, sin importar cuántas academias tengas dentro.

---

## 2. Estrategia Multi-Cliente Aislada con Costo $0

Para dar servicio a varias academias manteniendo sus datos 100% aislados y sin pagar servidores, se utiliza la **estrategia de cuentas independientes vinculadas**.

### El Truco de Alias de Correo (`+`) en Gmail
Para no tener que crear y verificar números telefónicos con múltiples correos de Google:
Si tu correo es `tucorreo@gmail.com`, puedes registrar cuentas independientes en Render y Supabase usando:
* `tucorreo+academia1@gmail.com`
* `tucorreo+academia2@gmail.com`
* `tucorreo+academia3@gmail.com`

* **Para las plataformas:** Son correos completamente independientes con su propio cupo gratuito (750 horas y 500 MB cada uno).
* **Para ti:** Todas las alertas, confirmaciones y avisos llegan a tu única bandeja de entrada principal.

### Organización Inteligente en GitHub
* **Mantén una sola cuenta de GitHub.**
* Crea un **repositorio privado por cada cliente** (`academia-marcelo`, `academia-tigres`, etc.).
* Conecta cada cuenta de Render con su repositorio correspondiente.
* **Ventaja:** Desde tu propia computadora puedes aplicar mejoras o cambios específicos para cada cliente mediante `git push` sin confusiones.

---

## 3. Modelo Comercial y Precios Sugeridos

### ¿Por qué NO cobrar por alumno o por registro?
Cobrar $0.50 o $1 por cada alumno crea **fricción psicológica negativa**: el cliente evitará registrar alumnos en periodo de prueba o suplentes para no gastar. Se busca que la academia use el sistema al 100%.

### Modelo Recomendado: Planes Escalonados (Tiered Pricing)

| Plan | Capacidad | Precio Mensual (USD) | Precio Mensual (Bolivia - Bs) |
| :--- | :--- | :---: | :---: |
| **Plan Formativo** | Hasta 40 alumnos | **$15 / mes** | ~100 a 120 Bs |
| **Plan Pro (Estándar)** | Hasta 120 alumnos | **$25 - $30 / mes** | ~180 a 220 Bs |
| **Plan Élite** | Alumnos ilimitados | **$45 - $50 / mes** | ~320 a 380 Bs |

### El Argumento de Cierre de Venta
> *"La mensualidad promedio que cobra la academia por alumno es de 150 a 250 Bs. Con que el sistema te ayude a detectar y cobrar a **un solo alumno que se estaba atrasando o pasando desapercibido**, el software ya se pagó completamente solo."*

### Estructura de Ingresos y Cobro
1. **Cobro de Configuración / Puesta en Marcha (Setup Fee - Pago Único):**
   * **$25 a $40 USD** (180 a 300 Bs).
   * Incluye: Cargar el logo institucional, colores oficiales de la academia, importación inicial del padrón de alumnos desde Excel y capacitación inicial al encargado.
2. **Descuento por Pago Anual (Genera Ingresos y Liquidez Anticipada):**
   * Ofrecer: **"Paga 10 meses y llévate 12 meses de servicio"** (2 meses bonificados).
   * Una academia que contrate el Plan Pro te pagará **$250 USD de golpe** al inicio del año.
3. **Justificación del Valor Mensual:**
   * Respaldo diario automático en la nube.
   * Soporte técnico y resolución de dudas por WhatsApp.
   * Acceso multidispositivo para entrenadores y administradores.

---

## 4. Seguridad, Prevención de Riesgos y Cero Sobrecostos

### ¿Puede haber cobros sorpresa por tráfico o bots?
* **En planes gratuitos (Render / Supabase):** No. Tienen límite estricto ("tope duro"). Si se supera la cuota, el servicio responde temporalmente con pausa; **nunca se efectúan cargos a tarjetas**.
* **En VPS fijo:** La tarifa es fija mensual ($4 - $5 USD). El tráfico extra no altera el monto.

### Protecciones de Seguridad Nativas del Sistema
1. **Sanitización de Imágenes y Prevención de Malware:**
   * Los archivos subidos no se almacenan directamente. Se procesan a través de la librería `Pillow` ([alumnos.py](file:///c:/Users/Usuario/.gemini/antigravity-ide/scratch/academia-futbol-marcelo/app/routes/alumnos.py)), verificando cabeceras reales de imagen y recompilando el mapa de bits.
   * Esto destruye scripts maliciosos (webshells PHP, HTML o ejecutables) camuflados en fotos.
   * Los nombres de archivo se reemplazan por identificadores criptográficos aleatorios (`uuid4`).
2. **Defensa contra Ataques de Fuerza Bruta:**
   * El sistema cuenta con **bloqueo por IP y tasa de intentos** en el login ([autenticacion.py](file:///c:/Users/Usuario/.gemini/antigravity-ide/scratch/academia-futbol-marcelo/app/routes/autenticacion.py)), respondiendo con código HTTP 429 tras reiterados intentos fallidos.
3. **Inyección SQL y CSRF:**
   * Consultas parametrizadas con SQLAlchemy ORM.
   * Formularios protegidos con tokens CSRF de sesión.

### Escudo Recomendado: Cloudflare (100% Gratuito)
Al conectar un dominio personalizado (ej. `gestiondeportiva.com`):
* Activa **Cloudflare Free**.
* Proporciona certificado SSL (HTTPS) automático.
* Filtra bots maliciosos, rastreadores automáticos y ataques DDoS antes de que alcancen tu servidor.

---

## 5. Documento Contractual y Legal Oficial

Para presentar formalmente a los clientes y firmar acuerdos de adhesión con respaldo legal y protección de datos, consulta el documento completo:
* [PROPUESTA_COMERCIAL_Y_MARCO_LEGAL.md](file:///c:/Users/Usuario/.gemini/antigravity-ide/scratch/academia-futbol-marcelo/docs/PROPUESTA_COMERCIAL_Y_MARCO_LEGAL.md): Incluye cláusulas de delimitación de responsabilidad, protección de datos de menores, retención de 30 días, SLA del 99% y modelos de firma.
