from __future__ import annotations

import re
import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models
from app.config import get_settings
from app.telegram_bot import format_money
from app.whatsapp_client import create_client_folder, open_client_folder, save_client_note


settings = get_settings()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def parse_priority(text: str) -> str:
    clean = normalize_text(text)
    for priority in ["urgente", "alta", "media", "baja"]:
        if re.search(rf"\b{priority}\b", clean):
            return priority
    return "media"


def next_weekday(day_index: int, today: date | None = None) -> date:
    base = today or date.today()
    delta = (day_index - base.weekday()) % 7
    return base + timedelta(days=delta or 7)


def parse_simple_date(text: str) -> date | None:
    clean = normalize_text(text)
    today = date.today()
    if "hoy" in clean:
        return today
    if "manana" in clean:
        return today + timedelta(days=1)

    weekdays = {
        "lunes": 0,
        "martes": 1,
        "miercoles": 2,
        "jueves": 3,
        "viernes": 4,
        "sabado": 5,
        "domingo": 6,
    }
    for name, index in weekdays.items():
        if re.search(rf"\b{name}\b", clean):
            return next_weekday(index, today)

    match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", clean)
    if match:
        day, month, year = match.groups()
        parsed_year = int(year) if year else today.year
        if parsed_year < 100:
            parsed_year += 2000
        return date(parsed_year, int(month), int(day))
    return None


def decimal_from_token(token: str) -> Decimal:
    return Decimal(token.replace("$", "").replace(".", "").replace(",", "."))


def help_text() -> str:
    return "\n".join(
        [
            "Hermes listo por WhatsApp.",
            "",
            "Comandos:",
            "ayuda",
            "resumen",
            "pendientes",
            "clientes",
            "proyectos",
            "tarea hacer post para manana prioridad alta",
            "cobro VAXA 120000 viernes web",
            "gasto Railway 5000 software",
            "reunion VAXA viernes 17 revisar web",
            "abrir carpeta VAXA",
            "crear carpeta VAXA",
            "nota VAXA revisar textos de la web",
            "confirmar ...",
            "rechazar ...",
        ]
    )


def build_summary(db: Session) -> str:
    summary = crud.finance_summary(db)
    tasks = crud.pending_tasks(db, limit=5)
    meetings = crud.upcoming_meetings(db, limit=5)
    charges = crud.pending_charges(db, limit=5)
    lines = [
        "Resumen Hermes",
        "",
        f"Tareas pendientes: {len(tasks)}",
        *[f"- {task.title} ({task.priority}, {task.due_date or 'sin fecha'})" for task in tasks],
        "",
        f"Reuniones proximas: {len(meetings)}",
        *[f"- {meeting.title} ({meeting.datetime.strftime('%d/%m %H:%M')})" for meeting in meetings],
        "",
        f"Cobros pendientes: {len(charges)}",
        *[f"- {charge.description or 'Cobro'}: {format_money(charge.amount)}" for charge in charges],
        "",
        f"Ingresos del mes: {format_money(summary['income_month'])}",
        f"Gastos del mes: {format_money(summary['expenses_month'])}",
        f"Ganancia estimada: {format_money(summary['estimated_profit'])}",
    ]
    return "\n".join(lines)


def build_pending(db: Session) -> str:
    tasks = crud.pending_tasks(db, limit=10)
    charges = crud.pending_charges(db, limit=10)
    return "\n".join(
        [
            "Pendientes",
            "",
            "Tareas:",
            *(f"- {task.title} ({task.priority}, {task.due_date or 'sin fecha'})" for task in tasks),
            *(["- Sin tareas pendientes"] if not tasks else []),
            "",
            "Cobros:",
            *(f"- {charge.description or 'Cobro'}: {format_money(charge.amount)} ({charge.status})" for charge in charges),
            *(["- Sin cobros pendientes"] if not charges else []),
        ]
    )


def build_clients(db: Session) -> str:
    clients = list(
        db.scalars(select(models.Client).where(models.Client.status == "activo").order_by(models.Client.name.asc())).all()
    )
    if not clients:
        return "No hay clientes activos."
    return "\n".join(["Clientes activos", *[f"- {client.name}" for client in clients]])


def build_projects(db: Session) -> str:
    projects = crud.active_projects(db)
    if not projects:
        return "No hay proyectos activos."
    return "\n".join(
        [
            "Proyectos activos",
            *[f"- {project.name} ({project.status}, {project.priority}, vence {project.due_date or 'sin fecha'})" for project in projects],
        ]
    )


def create_task(db: Session, text: str) -> str:
    content = re.sub(r"^/?tarea\s*", "", text, flags=re.IGNORECASE).strip()
    if not content:
        return "Uso: tarea hacer post para manana prioridad alta"
    priority = parse_priority(content)
    due_date = parse_simple_date(content)
    title = re.sub(r"\bprioridad\s+(baja|media|alta|urgente)\b", "", content, flags=re.IGNORECASE).strip()
    title = re.sub(r"\bpara\s+(hoy|manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b", "", title, flags=re.IGNORECASE).strip()
    created = crud.create(
        db,
        models.Task,
        {"title": title or content, "priority": priority, "due_date": due_date, "status": "pendiente"},
    )
    return f"Tarea creada #{created.id}: {created.title}"


def create_charge(db: Session, text: str) -> str:
    args = re.sub(r"^/?cobro\s*", "", text, flags=re.IGNORECASE).strip().split()
    if len(args) < 2:
        return "Uso: cobro VAXA 120000 viernes web"
    client_name = args[0]
    try:
        amount = decimal_from_token(args[1])
    except InvalidOperation:
        return "No pude leer el monto."
    rest = " ".join(args[2:])
    client = crud.find_client_by_name(db, client_name)
    created = crud.create(
        db,
        models.FinanceEntry,
        {
            "type": "ingreso",
            "category": args[-1] if len(args) >= 4 else "otros",
            "client_id": client.id if client else None,
            "amount": amount,
            "description": f"Cobro {client_name}",
            "due_date": parse_simple_date(rest),
            "status": "pendiente",
        },
    )
    return f"Cobro creado #{created.id}: {format_money(created.amount)}"


def create_expense(db: Session, text: str) -> str:
    args = re.sub(r"^/?gasto\s*", "", text, flags=re.IGNORECASE).strip().split()
    if len(args) < 2:
        return "Uso: gasto Railway 5000 software"
    try:
        amount = decimal_from_token(args[1])
    except InvalidOperation:
        return "No pude leer el monto."
    created = crud.create(
        db,
        models.FinanceEntry,
        {
            "type": "gasto",
            "category": args[2] if len(args) >= 3 else "otros",
            "amount": amount,
            "description": args[0],
            "paid_date": date.today(),
            "status": "pagado",
        },
    )
    return f"Gasto creado #{created.id}: {format_money(created.amount)}"


def create_meeting(db: Session, text: str) -> str:
    args = re.sub(r"^/?reunion\s*", "", text, flags=re.IGNORECASE).strip().split()
    if len(args) < 3:
        return "Uso: reunion VAXA viernes 17 revisar web"
    client_name = args[0]
    rest = " ".join(args[1:])
    meeting_date = parse_simple_date(rest) or date.today()
    hour = 9
    for token in args[1:]:
        if token.isdigit() and 0 <= int(token) <= 23:
            hour = int(token)
            break
    local_tz = ZoneInfo(settings.timezone)
    meeting_datetime = datetime.combine(meeting_date, time(hour=hour), tzinfo=local_tz).astimezone(UTC)
    client = crud.find_client_by_name(db, client_name)
    created = crud.create(
        db,
        models.Meeting,
        {
            "title": f"{client_name}: {rest}",
            "client_id": client.id if client else None,
            "datetime": meeting_datetime,
            "notes": rest,
            "status": "programada",
        },
    )
    return f"Reunion creada #{created.id}: {created.title}"


def save_note(db: Session, text: str) -> str:
    content = re.sub(r"^/?nota\s*", "", text, flags=re.IGNORECASE).strip()
    if not content or " " not in content:
        return "Uso: nota VAXA revisar textos de la web"
    client_name, note = content.split(" ", 1)
    client = crud.find_client_by_name(db, client_name)
    if client:
        previous = client.notes or ""
        stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        client.notes = f"{previous}\n[{stamp}] {note}".strip()
        db.add(client)
        db.commit()
    bridge_message = save_client_note(client_name, note)
    return f"Nota guardada para {client_name}. {bridge_message}"


def folder_command(text: str, action: str) -> str:
    client_name = re.sub(rf"^/?{action}\s+carpeta\s*", "", text, flags=re.IGNORECASE).strip()
    if not client_name:
        return f"Uso: {action} carpeta VAXA"
    if action == "abrir":
        return open_client_folder(client_name)
    return create_client_folder(client_name)


def process_known_command(db: Session, text: str) -> str | None:
    clean = normalize_text(text).lstrip("/")
    if clean in {"hola", "ayuda", "start"}:
        return help_text()
    if clean == "resumen":
        return build_summary(db)
    if clean == "pendientes":
        return build_pending(db)
    if clean == "clientes":
        return build_clients(db)
    if clean == "proyectos":
        return build_projects(db)
    if clean.startswith("tarea "):
        return create_task(db, text)
    if clean.startswith("cobro "):
        return create_charge(db, text)
    if clean.startswith("gasto "):
        return create_expense(db, text)
    if clean.startswith("reunion "):
        return create_meeting(db, text)
    if clean.startswith("abrir carpeta "):
        return folder_command(text, "abrir")
    if clean.startswith("crear carpeta "):
        return folder_command(text, "crear")
    if clean.startswith("nota "):
        return save_note(db, text)
    if clean.startswith("confirmar "):
        return "Confirmado. En esta version queda registrado como respuesta manual."
    if clean.startswith("rechazar "):
        return "Rechazado. En esta version queda registrado como respuesta manual."
    return None


def process_message(db: Session, text: str) -> str:
    known_reply = process_known_command(db, text)
    if known_reply is not None:
        return known_reply

    from app.ai_assistant import interpret_with_ai

    ai_reply = interpret_with_ai(db, text, lambda command: process_known_command(db, command) or help_text())
    if ai_reply:
        return ai_reply
    return "Comando no reconocido. Escribi ayuda para ver opciones."
