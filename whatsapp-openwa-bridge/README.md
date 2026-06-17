# Hermes OpenWA Bridge

Puente local para probar Hermes Secretario por WhatsApp usando QR con `@open-wa/wa-automate`.

Este puente usa WhatsApp Web por debajo. Es comodo para pruebas locales, pero no es la opcion recomendada para produccion. Para produccion conviene usar WhatsApp Cloud API oficial de Meta.

## Requisitos

- Node.js 18 o superior
- Hermes API corriendo, por ejemplo en `http://localhost:8000`
- Un telefono autorizado en `ADMIN_WHATSAPP_PHONE`

## Instalacion

```bash
cd whatsapp-openwa-bridge
copy .env.example .env
npm install
```

Editar `.env`:

```env
HERMES_API_URL=http://localhost:8000
ADMIN_WHATSAPP_PHONE=549XXXXXXXXXX
OPENWA_SESSION_ID=hermes-secretario
OPENWA_HEADLESS=false
```

## Correr

Primero levantar Hermes:

```bash
cd ..
docker compose up --build
```

En otra terminal:

```bash
cd whatsapp-openwa-bridge
npm start
```

Escanear el QR con WhatsApp. La sesion queda guardada localmente y esta ignorada por Git.

## Comandos soportados

```text
ayuda
resumen
pendientes
clientes
tarea hacer post para manana prioridad alta
cobro VAXA 120000 viernes web
gasto Railway 5000 software
reunion VAXA viernes 17 revisar web
```

## Seguridad

- El puente ignora mensajes si `ADMIN_WHATSAPP_PHONE` no esta configurado.
- Solo responde al numero autorizado.
- No subir archivos de sesion, `.env`, `tokens/` ni `session.data.json`.

