# 🚀 Guía de Migración a PostgreSQL y Despliegue en la Nube

Esta guía detalla los pasos para migrar el sistema **Academia de Fútbol** desde SQLite local hacia **PostgreSQL**, permitiendo alojar la base de datos y la aplicación en servicios cloud como **Render, Railway, Supabase, Neon o cualquier servidor VPS**.

---

## 📌 1. Novedades y Compatibilidad Incorporada

El sistema ahora cuenta con arquitectura **Dual (SQLite / PostgreSQL)**:
* **Detección inteligente de motor:** Si no se define `DATABASE_URL`, el sistema continúa operando localmente en SQLite sin requerir configuración adicional.
* **Compatibilidad cloud automática:** Corrige en caliente prefijos antiguos `postgres://` a `postgresql://` requeridos por SQLAlchemy.
* **Gestión de conexiones optimizada:** Configuración automática de pool (`pool_size`, `max_overflow`, `connect_timeout` y `pool_recycle`) al detectar PostgreSQL.
* **Driver de producción:** `psycopg2-binary` y servidor WSGI `gunicorn` integrados en [`requirements.txt`](../requirements.txt).
* **Migraciones seguras:** Esquema sincronizado con soporte para tipos nativos (`TIMESTAMP`, `BOOLEAN`, secuencias e índices parciales).

---

## 📦 2. Cómo Migrar tus Datos Existentes

Tienes dos métodos listos para transferir todos los alumnos, categorías, pagos, partidos y configuraciones actuales:

### Método A: Migración Directa con Script Python (Recomendado)
Ejecuta el script de migración indicando la URL de conexión de tu base de datos PostgreSQL remota o local:

```powershell
.\.venv\Scripts\python.exe scripts/migrar_a_postgresql.py --postgres "postgresql://usuario:contrasena@host:5432/nombre_bd"
```

O asignando la variable en tu terminal o `.env`:
```powershell
$env:DATABASE_URL="postgresql://usuario:contrasena@host:5432/nombre_bd"
.\.venv\Scripts\python.exe scripts/migrar_a_postgresql.py
```

**¿Qué hace el script automáticamente?**
1. Crea todas las 57 tablas en PostgreSQL con claves foráneas, restricciones e índices.
2. Transfiere todos los datos en orden topológico estricto para evitar violaciones de integridad referencial.
3. Convierte tipos booleanos SQLite (0/1) a tipos nativos PostgreSQL (`False`/`True`).
4. **Reinicia todas las secuencias (`setval`)** de las Primary Keys para que los nuevos registros creados en la web obtengan los IDs siguientes sin colisiones.
5. Registra las 32 migraciones en `schema_migration`.
6. Realiza una auditoría comparando fila por fila entre SQLite y PostgreSQL emitiendo un reporte de coincidencia.

---

### Método B: Exportación a Archivo SQL (Ideal para Supabase o Neon)
Si prefieres no conectar tu máquina local directamente a PostgreSQL, puedes generar un volcado SQL nativo:

```powershell
.\.venv\Scripts\python.exe scripts/exportar_para_postgresql.py
```

* **Salida generada:** [`instance/academia_postgresql.sql`](../instance/academia_postgresql.sql)
* **Cómo usarlo en la nube:**
  * En **Supabase**: Abre el **SQL Editor**, copia y pega el contenido del archivo `.sql` y pulsa **Run**.
  * En **Neon**: Abre la pestaña **SQL Editor**, pega el script y ejecuta.
  * Con **psql**:
    ```bash
    psql -h <host> -U <usuario> -d <base_datos> -f instance/academia_postgresql.sql
    ```

---

## ☁️ 3. Opciones de Despliegue en la Nube

### Opción 1: Render.com (Muy Fácil y Recomendado)
1. **Crear PostgreSQL en Render:**
   * Entra a [Render Dashboard](https://dashboard.render.com).
   * Pulsa **New +** ➔ **PostgreSQL**.
   * Elige un nombre (ej. `academia-db`), región y plan (Free o Starter).
   * Copia la **Internal Database URL** (o External Database URL).
2. **Migrar los datos:**
   * Ejecuta en tu máquina local:
     ```powershell
     .\.venv\Scripts\python.exe scripts/migrar_a_postgresql.py --postgres "TU_EXTERNAL_DATABASE_URL"
     ```
3. **Crear Web Service en Render:**
   * Conecta tu repositorio Git (GitHub/GitLab).
   * Selecciona **Python 3**.
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `gunicorn run:app --workers 2 --threads 4 --timeout 120`
   * En **Environment Variables**, añade:
     * `DATABASE_URL`: Tu cadena de conexión de PostgreSQL.
     * `SECRET_KEY`: Una clave aleatoria segura de 64 caracteres.
     * `FLASK_ENV`: `production`

---

### Opción 2: Railway.app
1. Crea un nuevo proyecto en [Railway](https://railway.app).
2. Añade un plugin de **PostgreSQL**.
3. Añade tu servicio web desde el repositorio GitHub.
4. Railway detectará automáticamente el archivo [`Procfile`](../Procfile) y la variable `DATABASE_URL` vinculada.
5. Ejecuta la migración de datos hacia la URL pública de Railway.

---

### Opción 3: Neon.tech / Supabase (Base de datos Cloud Gratuita) + Render/Fly.io
1. Crea un proyecto gratuito en [Neon](https://neon.tech) o [Supabase](https://supabase.com).
2. Obtén la cadena de conexión con SSL activado (`sslmode=require`).
3. Ejecuta [`scripts/migrar_a_postgresql.py`](../scripts/migrar_a_postgresql.py) apuntando a esa URL o corre [`instance/academia_postgresql.sql`](../instance/academia_postgresql.sql) en su consola.
4. En tu servidor web (Render, Fly.io, Railway, etc.), configura la variable de entorno `DATABASE_URL`.

---

### Opción 4: Docker Compose (Para VPS propio / Ubuntu / Debian)
Si tienes un servidor VPS (DigitalOcean, AWS EC2, Linode, Hetzner):
1. Clona el repositorio en el servidor.
2. Inicia los contenedores (PostgreSQL 16 + Web Gunicorn):
   ```bash
   docker compose up -d
   ```
3. Para migrar tus datos iniciales dentro del contenedor:
   ```bash
   docker compose exec web python scripts/migrar_a_postgresql.py --postgres "postgresql://academia_user:academia_password@db:5432/academia_futbol"
   ```

---

## 🔑 4. Variables de Entorno Requeridas en Producción

Configura estas variables en el panel de control de tu proveedor cloud:

| Variable | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `DATABASE_URL` | Conexión a PostgreSQL | `postgresql://user:pass@ep-xyz.aws.neon.tech/dbname?sslmode=require` |
| `SECRET_KEY` | Clave secreta para cookies de sesión | `4a8f9b2c3d1e...` (generar 64 caracteres hex) |
| `FLASK_ENV` | Modo de ejecución | `production` |
| `PORT` | Puerto asignado por el host (automático en Render/Railway) | `5000` o `$PORT` |

---

## ✅ 5. Verificación de Funcionamiento

Una vez desplegado:
1. Accede a tu dominio en la nube (ej. `https://mi-academia.onrender.com`).
2. Inicia sesión con tus credenciales de administrador existentes.
3. Ingresa a **Información General / Auditoría** para confirmar que todos los registros se encuentran sincronizados y sin errores de base de datos.
