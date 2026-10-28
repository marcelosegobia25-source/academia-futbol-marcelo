# 🚀 Guía de Despliegue en Render.com (Conectado a Supabase)

Esta guía explica cómo poner la **Academia de Fútbol** en la nube en **Render.com** enlazada a tu base de datos permanente en **Supabase**.

---

## 📋 Requisitos Previos
1. Una cuenta gratuita en [GitHub](https://github.com) con el repositorio actualizado: `https://github.com/marcelosegobia25-source/academia-futbol-marcelo`.
2. Una cuenta en [Render.com](https://render.com) (inicia sesión con tu cuenta de GitHub).
3. Tu base de datos de Supabase ya configurada (¡ya está lista con las 57 tablas y datos!).

---

## ⚡ Paso 1: Subir los Cambios a GitHub

Ejecuta en tu terminal:

```bash
git add .
git commit -m "Arquitectura modular, soporte Supabase PostgreSQL y preparacion Render"
git push origin main
```

---

## 🛠️ Paso 2: Crear el Web Service en Render (2 minutos)

1. Ingresa a tu panel: [dashboard.render.com](https://dashboard.render.com).
2. Haz clic en el botón superior **"New +"** y selecciona **"Web Service"**.
3. Selecciona la opción **"Build and deploy from a Git repository"** y haz clic en **Next**.
4. Conecta tu cuenta de GitHub y selecciona el repositorio **`academia-futbol-marcelo`**.
5. Configura los siguientes campos:
   - **Name:** `academia-futbol` (o el nombre que prefieras).
   - **Region:** `Oregon (US West)` (recomendado, más cercano al pooler de Supabase en `us-west-2`).
   - **Branch:** `main`.
   - **Runtime:** `Python 3`.
   - **Build Command:** `pip install -r requirements.txt`.
   - **Start Command:** `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`.
   - **Instance Type:** `Free` (Gratis).

---

## 🔐 Paso 3: Agregar las Variables de Entorno en Render

En la misma pantalla, baja hasta la sección **"Environment Variables"** y agrega:

| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql://postgres.qzgopliiayfgmrusvhqb:marcelosegobia....@aws-1-us-west-2.pooler.supabase.com:5432/postgres` |
| `SECRET_KEY` | *(Haz clic en "Generate" o pon una clave aleatoria)* |
| `FLASK_DEBUG` | `0` |
| `PYTHON_VERSION` | `3.11.9` |

6. Haz clic en el botón **"Deploy Web Service"** (abajo del todo).

---

## 🌐 Paso 4: ¡Tu Aplicación en la Nube!

En aproximadamente 2 minutos, Render compilará tu aplicación y te dará tu enlace público permanente:
👉 **`https://academia-futbol-xxxx.onrender.com`**

Podrás entrar desde tu teléfono, tablet o computadora con tu usuario:
- **Usuario:** `admin`
- **Contraseña:** `99999` *(o la contraseña con la que ingresas localmente)*

¡Todos los cambios que hagas se guardarán en Supabase en tiempo real!
