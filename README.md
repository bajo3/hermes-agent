# Hermes Secretario

Hermes Secretario es un agente personal tipo secretario para administrar clientes, proyectos, tareas, reuniones, finanzas basicas, cobros, gastos, recordatorios y resumenes diarios. Esta V1 esta pensada para correr en Railway Hobby con Docker, PostgreSQL y un bot de Telegram.

No usa WhatsApp Web, OCR, vision por computadora ni navegador headless.

## Stack

- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Pydantic v2
- Uvicorn
- python-telegram-bot
- APScheduler
- Docker y Docker Compose

## Decisiones tecnicas

- La API usa SQLAlchemy sincronico para mantener el deploy simple y estable.
- La base de datos principal es PostgreSQL. `DATABASE_URL` acepta tambien URLs `postgres://` y las normaliza a `postgresql://`.
- El proceso API solo sirve FastAPI. El proceso Worker ejecuta polling de Telegram y tareas periodicas.
- El Worker revisa recordatorios, marca cobros vencidos y envia avisos por Telegram.
- El resumen diario esta separado en `python -m app.daily_summary` para correrlo como Cron Job en Railway.
- El bot solo responde si `effective_user.id` coincide con `ADMIN_TELEGRAM_ID`.
- El parsing de comandos de Telegram es simple por diseno. Hay espacio para agregar IA/NLP en una version posterior.
- No se hardcodean tokens ni secretos. Todo se configura por variables de entorno.

## Funciones

- CRUD completo de clientes.
- CRUD completo de proyectos/trabajos.
- CRUD completo de tareas, con accion para completar.
- CRUD completo de reuniones.
- CRUD de finanzas, resumen, pendientes y marcar como pagado.
- CRUD de recordatorios.
- Dashboard HTML basico en `/`.
- Comandos de Telegram: `/start`, `/resumen`, `/tarea`, `/cobro`, `/gasto`, `/reunion`, `/pendientes`, `/clientes`.
- Worker para recordatorios y cobros vencidos.
- Resumen diario para Telegram.
- Script de seed con clientes y datos de ejemplo.

## Variables de entorno

Copiar `.env.example` a `.env` y completar:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hermes
SECRET_KEY=change_me
ENV=development
TELEGRAM_BOT_TOKEN=
ADMIN_TELEGRAM_ID=
TIMEZONE=America/Argentina/Buenos_Aires
```

`SECRET_KEY` queda preparada para futuras funciones de seguridad. Cambiala en produccion.

## Instalacion local sin Docker

Requisitos: Python 3.11 y PostgreSQL corriendo.

```bash
cd hermes-secretario
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Crear la base `hermes` en PostgreSQL y luego correr migraciones:

```bash
alembic upgrade head
```

Comandos utiles de Alembic:

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

## Correr API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abrir:

- Dashboard: http://localhost:8000/
- Health: http://localhost:8000/health
- Swagger: http://localhost:8000/docs

## Correr con Docker Compose

```bash
cd hermes-secretario
docker compose up --build
```

El servicio `app` espera a PostgreSQL, ejecuta `alembic upgrade head` y levanta la API en http://localhost:8000.

## Worker y bot

El worker mantiene el polling de Telegram y corre tareas periodicas.

```bash
python -m app.worker
```

Tambien se puede correr solo el bot:

```bash
python -m app.telegram_bot
```

Para usar Telegram:

1. Crear un bot con BotFather.
2. Guardar el token en `TELEGRAM_BOT_TOKEN`.
3. Obtener tu ID con User Info Bot.
4. Guardar ese numero en `ADMIN_TELEGRAM_ID`.

Comandos:

```text
/start
/resumen
/tarea hacer post de Romero para manana prioridad alta
/cobro VAXA 120000 viernes web
/gasto Railway 5000 software
/reunion VAXA viernes 17 revisar web
/pendientes
/clientes
```

## Resumen diario

```bash
python -m app.daily_summary
```

En Railway se recomienda correrlo como Cron Job a las 9:00 AM de Argentina con:

```text
0 12 * * *
```

Railway usa UTC y Argentina es UTC-3.

## Webhook WhatsApp Cloud API en Vercel

Hermes incluye un webhook oficial para Meta WhatsApp Cloud API:

```text
GET /webhooks/whatsapp
POST /webhooks/whatsapp
```

Variables necesarias en Vercel:

```bash
WHATSAPP_VERIFY_TOKEN=un_texto_secreto_elegido_por_vos
WHATSAPP_ACCESS_TOKEN=token_de_meta
WHATSAPP_PHONE_NUMBER_ID=id_del_numero_de_meta
ADMIN_WHATSAPP_PHONE=549XXXXXXXXXX
DATABASE_URL=postgresql://...
SECRET_KEY=...
ENV=production
TIMEZONE=America/Argentina/Buenos_Aires
```

URL para configurar en Meta:

```text
https://TU-DOMINIO-VERCEL.vercel.app/webhooks/whatsapp
```

Comandos soportados por WhatsApp en esta primera version:

- `resumen`
- `pendientes`
- `clientes`

## Prueba local con WhatsApp QR/OpenWA

Para probar rapido con QR sin Meta, el repo incluye un puente local en `whatsapp-openwa-bridge/`.

```bash
cd whatsapp-openwa-bridge
copy .env.example .env
npm install
npm start
```

Antes de correrlo, levantar Hermes en local:

```bash
docker compose up --build
```

El puente usa `@open-wa/wa-automate@4.76.0`, recibe mensajes de WhatsApp Web y llama a la API REST de Hermes. Es solo para pruebas/local; para produccion conviene usar WhatsApp Cloud API oficial de Meta.

## Seed de ejemplo

```bash
python -m app.seed
```

Crea clientes de ejemplo:

- VAXA Fumigaciones
- Romero Impermeabilizaciones
- JD Automotores
- Autos Tandil

Tambien crea proyectos, tareas y cobros de ejemplo.

## Endpoints principales

Health:

- `GET /health`

Clientes:

- `GET /clients`
- `POST /clients`
- `GET /clients/{id}`
- `PUT /clients/{id}`
- `DELETE /clients/{id}`

Proyectos:

- `GET /projects`
- `POST /projects`
- `GET /projects/{id}`
- `PUT /projects/{id}`
- `DELETE /projects/{id}`

Tareas:

- `GET /tasks`
- `POST /tasks`
- `GET /tasks/{id}`
- `PUT /tasks/{id}`
- `DELETE /tasks/{id}`
- `POST /tasks/{id}/complete`

Reuniones:

- `GET /meetings`
- `POST /meetings`
- `GET /meetings/{id}`
- `PUT /meetings/{id}`
- `DELETE /meetings/{id}`

Finanzas:

- `GET /finances`
- `POST /finances`
- `GET /finances/summary`
- `GET /finances/pending`
- `PUT /finances/{id}`
- `DELETE /finances/{id}`
- `POST /finances/{id}/mark-paid`

Recordatorios:

- `GET /reminders`
- `POST /reminders`
- `PUT /reminders/{id}`
- `DELETE /reminders/{id}`

Dashboard:

- `GET /`

## Railway

Los pasos completos estan en `DEPLOY_RAILWAY.md`.

Start commands documentados:

```bash
# API
uvicorn app.main:app --host 0.0.0.0 --port $PORT

# Worker
python -m app.worker

# Resumen diario / Cron
python -m app.daily_summary
```

Antes del primer deploy o cuando cambien modelos, correr:

```bash
alembic upgrade head
```

## Proximos pasos

- Agregar autenticacion para la API web.
- Agregar filtros por cliente, proyecto, estado y fecha.
- Mejorar NLP de comandos de Telegram con IA.
- Agregar tests automatizados.
- Agregar vistas HTML para crear y editar datos sin Swagger.
- Agregar webhooks de Telegram si se prefiere evitar polling.
