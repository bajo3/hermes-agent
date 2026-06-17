require('dotenv').config();

function required(name, fallback = '') {
  const value = process.env[name] || fallback;
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

function normalizeNumber(value) {
  return String(value || '').replace(/\D/g, '');
}

const config = {
  hermesApiUrl: required('HERMES_API_URL', 'http://api:8000').replace(/\/$/, ''),
  bridgeToken: required('WHATSAPP_BRIDGE_TOKEN', 'change_me_bridge_token'),
  adminNumber: normalizeNumber(required('ADMIN_WHATSAPP_NUMBER')),
  authDir: process.env.WHATSAPP_AUTH_DIR || './auth',
  logFile: process.env.WHATSAPP_LOG_FILE || './logs/messages.log',
  rejectUnauthorized: String(process.env.WHATSAPP_REJECT_UNAUTHORIZED || 'false').toLowerCase() === 'true',
};

module.exports = { config, normalizeNumber };

