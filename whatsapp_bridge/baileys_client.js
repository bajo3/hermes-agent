const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode-terminal');
const pino = require('pino');
const { Boom } = require('@hapi/boom');
const {
  default: makeWASocket,
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} = require('@whiskeysockets/baileys');

const { config, normalizeNumber } = require('./config');

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function appendLog(event) {
  ensureDir(path.dirname(config.logFile));
  fs.appendFileSync(config.logFile, `${JSON.stringify({ at: new Date().toISOString(), ...event })}\n`);
}

function jidToNumber(jid) {
  return normalizeNumber(String(jid || '').split('@')[0]);
}

function isGroupMessage(message) {
  return String(message.key.remoteJid || '').endsWith('@g.us');
}

function extractText(message) {
  const content = message.message || {};
  return (
    content.conversation ||
    content.extendedTextMessage?.text ||
    content.imageMessage?.caption ||
    content.videoMessage?.caption ||
    ''
  ).trim();
}

function isAdminMessage(message) {
  const fromNumber = jidToNumber(message.key.remoteJid);
  return fromNumber === config.adminNumber;
}

async function sendToHermes({ fromNumber, text, messageId, timestamp }) {
  const response = await fetch(`${config.hermesApiUrl}/internal/whatsapp/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Whatsapp-Bridge-Token': config.bridgeToken,
    },
    body: JSON.stringify({
      from_number: fromNumber,
      text,
      message_id: messageId,
      timestamp,
    }),
  });

  const bodyText = await response.text();
  if (!response.ok) {
    throw new Error(`Hermes ${response.status}: ${bodyText}`);
  }
  return JSON.parse(bodyText).reply || '';
}

async function startBaileys() {
  ensureDir(config.authDir);
  ensureDir(path.dirname(config.logFile));

  const { state, saveCreds } = await useMultiFileAuthState(config.authDir);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: 'warn' }),
    printQRInTerminal: false,
    browser: ['Hermes Secretario', 'Chrome', '1.0.0'],
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      console.log('Escanea este QR con WhatsApp:');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'open') {
      console.log('WhatsApp conectado.');
      appendLog({ direction: 'system', status: 'connected' });
    }

    if (connection === 'close') {
      const statusCode = new Boom(lastDisconnect?.error).output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      console.log(`WhatsApp desconectado. Reconnect=${shouldReconnect}`);
      appendLog({ direction: 'system', status: 'disconnected', statusCode });
      if (shouldReconnect) {
        setTimeout(() => startBaileys().catch(console.error), 3000);
      } else {
        console.log('Sesion cerrada. Borra whatsapp_bridge/auth y escanea QR otra vez.');
      }
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const message of messages) {
      if (!message.message || message.key.fromMe) continue;
      if (isGroupMessage(message)) {
        appendLog({ direction: 'incoming', status: 'ignored_group', messageId: message.key.id });
        continue;
      }

      const fromNumber = jidToNumber(message.key.remoteJid);
      const text = extractText(message);
      if (!text) continue;

      appendLog({ direction: 'incoming', fromNumber, messageId: message.key.id, text });

      if (!isAdminMessage(message)) {
        appendLog({ direction: 'incoming', fromNumber, messageId: message.key.id, status: 'unauthorized' });
        if (config.rejectUnauthorized) {
          await sock.sendMessage(message.key.remoteJid, { text: 'No autorizado.' });
        }
        continue;
      }

      try {
        const reply = await sendToHermes({
          fromNumber,
          text,
          messageId: message.key.id,
          timestamp: message.messageTimestamp ? String(message.messageTimestamp) : new Date().toISOString(),
        });
        if (reply) {
          await sock.sendMessage(message.key.remoteJid, { text: reply });
          appendLog({ direction: 'outgoing', fromNumber, messageId: message.key.id, text: reply, status: 'sent' });
        }
      } catch (error) {
        console.error(error);
        appendLog({ direction: 'error', fromNumber, messageId: message.key.id, error: error.message });
        await sock.sendMessage(message.key.remoteJid, { text: `Error hablando con Hermes: ${error.message}` });
      }
    }
  });

  return sock;
}

module.exports = { startBaileys };

