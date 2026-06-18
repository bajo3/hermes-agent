# Hermes Secretario

Hermes Secretario es un agente personal para administrar clientes, proyectos, tareas, reuniones, cobros, gastos, recordatorios y resumenes diarios.

La integracion de WhatsApp de esta version usa **Baileys** en un servicio Node.js local con QR y sesion persistente.

## Arquitectura

```text
WhatsApp -> Baileys Bridge -> FastAPI Hermes -> PostgreSQL
                              |
                              -> Windows Bridge -> PC Windows
```

Servicios principales:

- `api`: FastAPI con SQLAlchemy, Alembic y dashboard.
- `db`: PostgreSQL.
- `worker`: recordatorios, cobros vencidos y tareas programadas.
- `whatsapp_bridge`: Node.js + Baileys, login por QR y sesion persistente.
- `windows_bridge`: reservado para acciones locales de Windows.

## Stack

- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- Uvicorn
- APScheduler
- Node.js 20
- Baileys
- Docker Compose

## Variables de entorno

Copiar `.env.example` a `.env`:

```bash
copy .env.example .env
```

Variables principales:

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/hermes
SECRET_KEY=change_me
ENV=development
TIMEZONE=America/Argentina/Buenos_Aires

ADMIN_WHATSAPP_NUMBER=549XXXXXXXXXX

HERMES_API_URL=http://api:8000
WHATSAPP_BRIDGE_TOKEN=change_me_bridge_token

BRIDGE_URL=http://host.docker.internal:8765
BRIDGE_TOKEN=change_me_windows_bridge_token

APP_HOST=0.0.0.0
APP_PORT=8000

DEFAULT_CLIENTS_FOLDER=C:\Hermes\Clientes
DEFAULT_BACKUP_FOLDER=C:\Hermes\Backups
DEFAULT_EXPORTS_FOLDER=C:\Hermes\Exports

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
AI_ENABLED=true
AI_PROVIDER=openai
AI_HISTORY_MESSAGES=12
AI_HISTORY_MINUTES=30

HERMES_CLI_PROVIDER=openai-codex
HERMES_CLI_MODEL=gpt-5.5
HERMES_CLI_TIMEOUT=120
HERMES_CLI_BRIDGE_URL=http://host.docker.internal:8766/interpret
HERMES_CLI_BRIDGE_TOKEN=
```

`ADMIN_WHATSAPP_NUMBER` debe ir con codigo de pais y sin `+`, espacios ni guiones.

## Correr con Docker Compose

```bash
docker compose up --build
```

En el primer inicio, `whatsapp_bridge` muestra un QR en consola. Escanealo con WhatsApp desde Dispositivos vinculados.

La sesion queda guardada en:

```text
whatsapp_bridge/auth
```

No subas esa carpeta a GitHub. Ya esta protegida por `.gitignore`.

## Reiniciar sesion de WhatsApp

Si se desloguea o queres vincular otro telefono:

1. Parar `whatsapp_bridge`.
2. Borrar el contenido de `whatsapp_bridge/auth`, dejando `.gitkeep`.
3. Ejecutar `docker compose up --build`.
4. Escanear el nuevo QR.

## Endpoint interno de WhatsApp

Baileys llama a FastAPI por red interna:

```text
POST /internal/whatsapp/message
```

Header:

```text
X-Whatsapp-Bridge-Token: WHATSAPP_BRIDGE_TOKEN
```

Body:

```json
{
  "from_number": "549...",
  "text": "resumen",
  "message_id": "...",
  "timestamp": "..."
}
```

FastAPI valida token, valida `ADMIN_WHATSAPP_NUMBER`, loguea entrada y salida, procesa el comando y devuelve:

```json
{
  "reply": "texto de respuesta"
}
```

## Comandos WhatsApp

```text
ayuda
resumen
pendientes
clientes
proyectos
tarea hacer post de Romero para manana prioridad alta
completar tarea hacer post
cancelar tarea 12
prioridad tarea hacer post urgente
cobro VAXA 120000 viernes web
gasto Railway 5000 software
reunion VAXA viernes 17 revisar web
abrir carpeta VAXA
crear carpeta VAXA
nota VAXA revisar textos de la web
confirmar ...
rechazar ...
```

Si `AI_ENABLED=true`, Hermes tambien interpreta mensajes naturales. Los comandos exactos siempre se procesan primero.
El historial reciente de cada numero se toma de PostgreSQL para resolver respuestas breves y aclaraciones. Por defecto conserva 12 mensajes dentro de una ventana de 30 minutos para el contexto de la IA.

Hay dos proveedores soportados:

- `AI_PROVIDER=openai`: usa `OPENAI_API_KEY`.
- `AI_PROVIDER=hermes_http`: usa el Hermes de WSL con tu OAuth de `openai-codex`.

Para usar Codex OAuth local desde Docker, primero levanta el puente en WSL:

```bash
cd /mnt/c/Users/felip/Desktop/Feli\ Web/hermes\ agent/hermes-secretario
export HERMES_AI_BRIDGE_TOKEN=hermes_codex_local
python3 wsl_hermes_bridge/hermes_ai_bridge.py
```

Luego en `.env`:

```text
AI_PROVIDER=hermes_http
HERMES_CLI_PROVIDER=openai-codex
HERMES_CLI_MODEL=gpt-5.5
HERMES_CLI_BRIDGE_URL=http://host.docker.internal:8766/interpret
HERMES_CLI_BRIDGE_TOKEN=hermes_codex_local
```

Ejemplos:

```text
manana recordame revisar la web de VAXA con prioridad alta
cargame un cobro de 120000 a VAXA para el viernes por web
anotame en Romero que falta revisar textos
```

## Seguridad

- El bridge ignora grupos.
- Solo responde al numero de `ADMIN_WHATSAPP_NUMBER`.
- Puede ignorar desconocidos sin responder.
- Usa `WHATSAPP_BRIDGE_TOKEN` para hablar con FastAPI.
- Guarda logs en base de datos y en `whatsapp_bridge/logs/messages.log`.
- `.env`, `whatsapp_bridge/auth` y logs locales estan ignorados por Git.

## Correr API sin Docker

Requisitos: Python 3.11 y PostgreSQL.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abrir:

- Dashboard: http://localhost:8000/
- Health: http://localhost:8000/health
- Swagger: http://localhost:8000/docs

## Correr Baileys sin Docker

```bash
cd whatsapp_bridge
npm install
npm start
```

Si Hermes corre local sin Docker:

```env
HERMES_API_URL=http://localhost:8000
```

## Migraciones

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

## Seed

```bash
python -m app.seed
```

Crea datos de ejemplo para:

- VAXA Fumigaciones
- Romero Impermeabilizaciones
- JD Automotores
- Autos Tandil

## Endpoints REST principales

- `GET /health`
- `GET /clients`
- `POST /clients`
- `GET /projects`
- `POST /projects`
- `GET /tasks`
- `POST /tasks`
- `POST /tasks/{id}/complete`
- `GET /meetings`
- `POST /meetings`
- `GET /finances`
- `POST /finances`
- `GET /finances/summary`
- `GET /finances/pending`
- `POST /finances/{id}/mark-paid`
- `GET /reminders`
- `POST /reminders`

## Railway

Railway puede correr `api`, `db` y `worker`. El bridge Baileys esta pensado para correr localmente en Windows/WSL o en un entorno donde puedas mantener la sesion QR persistente.

Start command API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Worker:

```bash
python -m app.worker
```

Migracion:

```bash
alembic upgrade head
```

## Proximos pasos

- Implementar el Windows Bridge real para abrir/crear carpetas.
- Agregar IA para interpretar mensajes naturales.
- Agregar autenticacion para dashboard/API publica.
- Agregar tests automatizados.
