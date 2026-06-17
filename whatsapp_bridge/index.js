const { config } = require('./config');
const { startBaileys } = require('./baileys_client');

console.log('Hermes WhatsApp Bridge iniciando...');
console.log(`Hermes API: ${config.hermesApiUrl}`);
console.log(`Admin WhatsApp: ${config.adminNumber}`);
console.log(`Auth dir: ${config.authDir}`);

startBaileys().catch((error) => {
  console.error(error);
  process.exit(1);
});

