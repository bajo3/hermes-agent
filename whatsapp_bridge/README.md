# Hermes WhatsApp Bridge

Servicio local de WhatsApp para Hermes usando Node.js y Baileys.

Se conecta mediante Linked Devices y QR, guardando la sesion localmente.

## Variables

```env
ADMIN_WHATSAPP_NUMBER=549XXXXXXXXXX
HERMES_API_URL=http://api:8000
WHATSAPP_BRIDGE_TOKEN=change_me_bridge_token
WHATSAPP_AUTH_DIR=./auth
WHATSAPP_LOG_FILE=./logs/messages.log
```

## Local

```bash
cd whatsapp_bridge
npm install
npm start
```

En el primer inicio aparece un QR en consola. Escanealo desde WhatsApp. La sesion queda guardada en `whatsapp_bridge/auth`.

## Seguridad

- Ignora grupos.
- Solo responde al numero configurado en `ADMIN_WHATSAPP_NUMBER`.
- Usa `WHATSAPP_BRIDGE_TOKEN` para hablar con FastAPI.
- No subir `auth/` ni logs a GitHub.

## Reset de sesion

Si WhatsApp se desloguea:

1. Parar el bridge.
2. Borrar el contenido de `whatsapp_bridge/auth` dejando `.gitkeep`.
3. Ejecutar `npm start`.
4. Escanear el nuevo QR.
