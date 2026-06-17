require('dotenv').config();

const { create } = require('@open-wa/wa-automate');

const HERMES_API_URL = (process.env.HERMES_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const ADMIN_WHATSAPP_PHONE = normalizePhone(process.env.ADMIN_WHATSAPP_PHONE);
const OPENWA_SESSION_ID = process.env.OPENWA_SESSION_ID || 'hermes-secretario';
const OPENWA_HEADLESS = String(process.env.OPENWA_HEADLESS || 'false').toLowerCase() === 'true';

function normalizePhone(value) {
  return String(value || '').replace(/\D/g, '');
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function nextWeekday(dayIndex) {
  const today = new Date();
  const date = new Date(today);
  const delta = (dayIndex - today.getDay() + 7) % 7 || 7;
  date.setDate(today.getDate() + delta);
  return date.toISOString().slice(0, 10);
}

function parseSimpleDate(text) {
  const clean = normalizeText(text);
  const now = new Date();

  if (/\bhoy\b/.test(clean)) return todayISO();
  if (/\bmanana\b/.test(clean)) {
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    return tomorrow.toISOString().slice(0, 10);
  }

  const weekdays = {
    domingo: 0,
    lunes: 1,
    martes: 2,
    miercoles: 3,
    jueves: 4,
    viernes: 5,
    sabado: 6,
  };

  for (const [name, index] of Object.entries(weekdays)) {
    if (new RegExp(`\\b${name}\\b`).test(clean)) return nextWeekday(index);
  }

  const match = clean.match(/\b(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\b/);
  if (match) {
    const day = Number(match[1]);
    const month = Number(match[2]) - 1;
    let year = match[3] ? Number(match[3]) : now.getFullYear();
    if (year < 100) year += 2000;
    return new Date(year, month, day).toISOString().slice(0, 10);
  }

  return null;
}

function parsePriority(text) {
  const clean = normalizeText(text);
  for (const priority of ['urgente', 'alta', 'media', 'baja']) {
    if (new RegExp(`\\b${priority}\\b`).test(clean)) return priority;
  }
  return 'media';
}

function normalizeText(text) {
  return String(text || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function money(value) {
  const amount = Number(value || 0);
  return amount.toLocaleString('es-AR', { style: 'currency', currency: 'ARS' });
}

async function hermes(path, options = {}) {
  const response = await fetch(`${HERMES_API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Hermes ${response.status} ${path}: ${body}`);
  }

  if (response.status === 204) return null;
  return response.json();
}

async function findClientIdByName(name) {
  if (!name) return null;
  const clients = await hermes('/clients');
  const cleanName = normalizeText(name);
  const match = clients.find((client) => normalizeText(client.name).includes(cleanName));
  return match ? match.id : null;
}

async function commandResumen() {
  const [summary, tasks, meetings, pending] = await Promise.all([
    hermes('/finances/summary'),
    hermes('/tasks'),
    hermes('/meetings'),
    hermes('/finances/pending'),
  ]);

  const pendingTasks = tasks.filter((task) => ['pendiente', 'en_progreso'].includes(task.status)).slice(0, 5);
  const upcomingMeetings = meetings
    .filter((meeting) => meeting.status !== 'cancelada' && new Date(meeting.datetime) >= new Date())
    .sort((a, b) => new Date(a.datetime) - new Date(b.datetime))
    .slice(0, 5);
  const pendingCharges = pending.filter((entry) => entry.type === 'ingreso').slice(0, 5);

  return [
    'Resumen Hermes',
    '',
    `Tareas pendientes: ${pendingTasks.length}`,
    ...pendingTasks.map((task) => `- ${task.title} (${task.priority}, ${task.due_date || 'sin fecha'})`),
    '',
    `Reuniones proximas: ${upcomingMeetings.length}`,
    ...upcomingMeetings.map((meeting) => `- ${meeting.title} (${new Date(meeting.datetime).toLocaleString('es-AR')})`),
    '',
    `Cobros pendientes: ${pendingCharges.length}`,
    ...pendingCharges.map((entry) => `- ${entry.description || 'Cobro'}: ${money(entry.amount)}`),
    '',
    `Ingresos del mes: ${money(summary.income_month)}`,
    `Gastos del mes: ${money(summary.expenses_month)}`,
    `Ganancia estimada: ${money(summary.estimated_profit)}`,
  ].join('\n');
}

async function commandPendientes() {
  const [tasks, pending] = await Promise.all([hermes('/tasks'), hermes('/finances/pending')]);
  const pendingTasks = tasks.filter((task) => ['pendiente', 'en_progreso'].includes(task.status)).slice(0, 10);
  const pendingCharges = pending.filter((entry) => entry.type === 'ingreso').slice(0, 10);

  return [
    'Pendientes',
    '',
    'Tareas:',
    ...(pendingTasks.length ? pendingTasks.map((task) => `- ${task.title} (${task.priority}, ${task.due_date || 'sin fecha'})`) : ['- Sin tareas pendientes']),
    '',
    'Cobros:',
    ...(pendingCharges.length ? pendingCharges.map((entry) => `- ${entry.description || 'Cobro'}: ${money(entry.amount)} (${entry.status})`) : ['- Sin cobros pendientes']),
  ].join('\n');
}

async function commandClientes() {
  const clients = await hermes('/clients');
  const active = clients.filter((client) => client.status === 'activo');
  if (!active.length) return 'No hay clientes activos.';
  return ['Clientes activos', ...active.map((client) => `- ${client.name}`)].join('\n');
}

async function commandTarea(rawText) {
  const text = rawText.replace(/^\/?tarea\s*/i, '').trim();
  if (!text) return 'Uso: tarea hacer post para manana prioridad alta';

  const priority = parsePriority(text);
  const dueDate = parseSimpleDate(text);
  const title = text
    .replace(/\bprioridad\s+(baja|media|alta|urgente)\b/i, '')
    .replace(/\bpara\s+(hoy|manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b/i, '')
    .trim();

  const created = await hermes('/tasks', {
    method: 'POST',
    body: JSON.stringify({
      title: title || text,
      priority,
      due_date: dueDate,
      status: 'pendiente',
    }),
  });

  return `Tarea creada #${created.id}: ${created.title}`;
}

async function commandCobro(rawText) {
  const args = rawText.replace(/^\/?cobro\s*/i, '').trim().split(/\s+/).filter(Boolean);
  if (args.length < 2) return 'Uso: cobro VAXA 120000 viernes web';

  const clientName = args[0];
  const amount = Number(String(args[1]).replace(/\./g, '').replace(',', '.'));
  if (!Number.isFinite(amount)) return 'No pude leer el monto.';

  const rest = args.slice(2).join(' ');
  const category = args.length >= 4 ? args[args.length - 1] : 'otros';
  const clientId = await findClientIdByName(clientName);
  const created = await hermes('/finances', {
    method: 'POST',
    body: JSON.stringify({
      type: 'ingreso',
      category,
      client_id: clientId,
      amount,
      description: `Cobro ${clientName}`,
      due_date: parseSimpleDate(rest),
      status: 'pendiente',
    }),
  });

  return `Cobro creado #${created.id}: ${money(created.amount)}`;
}

async function commandGasto(rawText) {
  const args = rawText.replace(/^\/?gasto\s*/i, '').trim().split(/\s+/).filter(Boolean);
  if (args.length < 2) return 'Uso: gasto Railway 5000 software';

  const description = args[0];
  const amount = Number(String(args[1]).replace(/\./g, '').replace(',', '.'));
  if (!Number.isFinite(amount)) return 'No pude leer el monto.';

  const created = await hermes('/finances', {
    method: 'POST',
    body: JSON.stringify({
      type: 'gasto',
      category: args[2] || 'otros',
      amount,
      description,
      paid_date: todayISO(),
      status: 'pagado',
    }),
  });

  return `Gasto creado #${created.id}: ${money(created.amount)}`;
}

async function commandReunion(rawText) {
  const args = rawText.replace(/^\/?reunion\s*/i, '').trim().split(/\s+/).filter(Boolean);
  if (args.length < 3) return 'Uso: reunion VAXA viernes 17 revisar web';

  const clientName = args[0];
  const rest = args.slice(1).join(' ');
  const dueDate = parseSimpleDate(rest) || todayISO();
  const hourToken = args.slice(1).find((token) => /^\d{1,2}$/.test(token) && Number(token) >= 0 && Number(token) <= 23);
  const hour = hourToken ? Number(hourToken) : 9;
  const dateTime = new Date(`${dueDate}T${String(hour).padStart(2, '0')}:00:00-03:00`).toISOString();
  const clientId = await findClientIdByName(clientName);

  const title = args
    .slice(1)
    .filter((token) => token !== hourToken)
    .join(' ')
    .trim() || `Reunion ${clientName}`;

  const created = await hermes('/meetings', {
    method: 'POST',
    body: JSON.stringify({
      title: `${clientName}: ${title}`,
      client_id: clientId,
      datetime: dateTime,
      notes: rest,
      status: 'programada',
    }),
  });

  return `Reunion creada #${created.id}: ${created.title}`;
}

async function handleCommand(text) {
  const clean = normalizeText(text).replace(/^\//, '');
  if (['hola', 'ayuda', 'start'].includes(clean)) {
    return [
      'Hermes listo por WhatsApp QR.',
      '',
      'Comandos:',
      'resumen',
      'pendientes',
      'clientes',
      'tarea hacer post para manana prioridad alta',
      'cobro VAXA 120000 viernes web',
      'gasto Railway 5000 software',
      'reunion VAXA viernes 17 revisar web',
    ].join('\n');
  }
  if (clean === 'resumen') return commandResumen();
  if (clean === 'pendientes') return commandPendientes();
  if (clean === 'clientes') return commandClientes();
  if (clean.startsWith('tarea ')) return commandTarea(text);
  if (clean.startsWith('cobro ')) return commandCobro(text);
  if (clean.startsWith('gasto ')) return commandGasto(text);
  if (clean.startsWith('reunion ')) return commandReunion(text);
  return 'Comando no reconocido. Proba con: resumen, pendientes, clientes, tarea, cobro, gasto o reunion.';
}

function isAuthorized(message) {
  const from = normalizePhone(message.from || message.sender?.id);
  if (!ADMIN_WHATSAPP_PHONE) {
    console.warn('ADMIN_WHATSAPP_PHONE is not configured. Ignoring messages for safety.');
    return false;
  }
  return from.includes(ADMIN_WHATSAPP_PHONE) || ADMIN_WHATSAPP_PHONE.includes(from);
}

async function main() {
  console.log(`Connecting OpenWA session "${OPENWA_SESSION_ID}"`);
  console.log(`Hermes API: ${HERMES_API_URL}`);
  console.log('Scan the QR when the browser/terminal asks for it.');

  const client = await create({
    sessionId: OPENWA_SESSION_ID,
    multiDevice: true,
    headless: OPENWA_HEADLESS,
    qrTimeout: 0,
    authTimeout: 0,
    useChrome: true,
  });

  console.log('OpenWA bridge ready.');

  client.onMessage(async (message) => {
    try {
      if (message.isGroupMsg) return;
      if (!message.body || !isAuthorized(message)) return;

      const response = await handleCommand(message.body);
      await client.sendText(message.from, response);
    } catch (error) {
      console.error(error);
      await client.sendText(message.from, `Error hablando con Hermes: ${error.message}`);
    }
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

