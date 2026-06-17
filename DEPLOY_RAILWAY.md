# Deploy en Railway

Guia para desplegar Hermes Secretario en Railway Hobby con Docker, PostgreSQL y Telegram Bot.

Links utiles:

- Railway: https://railway.com
- Crear nuevo proyecto Railway: https://railway.com/new
- GitHub nuevo repo: https://github.com/new
- BotFather Telegram: https://t.me/BotFather
- User Info Bot Telegram: https://t.me/userinfobot

## 1. Crear repo en GitHub

Entrar a https://github.com/new, crear un repositorio nuevo y subir el contenido de `hermes-secretario`.

Ejemplo:

```bash
cd hermes-secretario
git init
git add .
git commit -m "Initial Hermes Secretario"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/hermes-secretario.git
git push -u origin main
```

## 2. Crear proyecto en Railway desde GitHub

1. Entrar a https://railway.com/new.
2. Elegir "Deploy from GitHub repo".
3. Seleccionar el repo `hermes-secretario`.
4. Railway detecta el `Dockerfile` y construye la imagen.

## 3. Agregar PostgreSQL

1. Dentro del proyecto Railway, elegir "New".
2. Elegir "Database".
3. Elegir "Add PostgreSQL".
4. Copiar o referenciar la variable `DATABASE_URL` que Railway genera.

## 4. Configurar variables

En el servicio API y tambien en el servicio Worker configurar:

```text
DATABASE_URL=<la DATABASE_URL de Railway PostgreSQL>
SECRET_KEY=<un secreto largo>
ENV=production
TELEGRAM_BOT_TOKEN=<token de BotFather>
ADMIN_TELEGRAM_ID=<tu id numerico de Telegram>
TIMEZONE=America/Argentina/Buenos_Aires
```

Notas:

- `TELEGRAM_BOT_TOKEN` se consigue creando el bot en https://t.me/BotFather.
- `ADMIN_TELEGRAM_ID` se consigue hablando con https://t.me/userinfobot.
- El bot rechaza cualquier usuario que no coincida con `ADMIN_TELEGRAM_ID`.

## 5. Crear servicio API

El servicio principal debe usar este Start Command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Railway asigna `PORT` automaticamente.

Despues de crear la base, correr migraciones una vez desde la terminal/shell del servicio o con un job temporal:

```bash
alembic upgrade head
```

## 6. Generar dominio publico

1. Entrar al servicio API.
2. Ir a "Settings".
3. Buscar "Networking".
4. Crear dominio publico.
5. Probar:

```text
https://TU-DOMINIO.railway.app/health
```

Debe responder:

```json
{
  "status": "ok",
  "service": "hermes-secretario"
}
```

## 7. Crear servicio Worker

Crear otro servicio dentro del mismo proyecto Railway usando el mismo repo.

Start Command:

```bash
python -m app.worker
```

Este proceso:

- Corre el polling del bot de Telegram.
- Revisa recordatorios pendientes.
- Marca cobros vencidos.
- Envia avisos al administrador por Telegram.

## 8. Crear Cron Job para resumen diario

Crear un Cron Job en Railway usando el mismo repo e imagen.

Command:

```bash
python -m app.daily_summary
```

Cron sugerido para Argentina 9:00 AM:

```text
0 12 * * *
```

Railway usa UTC. Argentina es UTC-3, por eso 9:00 AM Argentina equivale a 12:00 UTC.

## 9. Verificaciones despues del deploy

1. Abrir `/health`.
2. Abrir `/docs`.
3. Abrir `/`.
4. Enviar `/start` al bot de Telegram.
5. Probar:

```text
/tarea revisar deploy para manana prioridad alta
/gasto Railway 5000 software
/cobro VAXA 120000 viernes web
/resumen
```

## 10. Comandos Railway documentados

API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Worker:

```bash
python -m app.worker
```

Resumen diario / Cron:

```bash
python -m app.daily_summary
```

