import asyncio
import re
import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app import crud, models
from app.config import get_settings
from app.database import SessionLocal


settings = get_settings()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(settings.admin_telegram_id and user and user.id == settings.admin_telegram_id)


async def reject_if_not_admin(update: Update) -> bool:
    if is_admin(update):
        return False
    if update.effective_chat:
        await update.effective_chat.send_message("No autorizado.")
    return True


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


def parse_priority(text: str) -> str:
    clean = normalize_text(text)
    for priority in ["urgente", "alta", "media", "baja"]:
        if re.search(rf"\b{priority}\b", clean):
            return priority
    return "media"


def decimal_from_token(token: str) -> Decimal:
    cleaned = token.replace("$", "").replace(".", "").replace(",", ".")
    return Decimal(cleaned)


def format_money(value: Decimal) -> str:
    return f"${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_summary(db: Session) -> str:
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    await update.message.reply_text(
        "\n".join(
            [
                "Hermes Secretario listo.",
                "",
                "Comandos:",
                "/resumen",
                "/tarea hacer post para manana prioridad alta",
                "/cobro VAXA 120000 viernes web",
                "/gasto Railway 5000 software",
                "/reunion VAXA viernes 17 revisar web",
                "/pendientes",
                "/clientes",
            ]
        )
    )


async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    with SessionLocal() as db:
        await update.message.reply_text(format_summary(db))


async def tarea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Uso: /tarea hacer post para manana prioridad alta")
        return
    priority = parse_priority(text)
    due_date = parse_simple_date(text)
    title = re.sub(r"\bprioridad\s+(baja|media|alta|urgente)\b", "", text, flags=re.IGNORECASE).strip()
    title = re.sub(r"\bpara\s+(hoy|manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b", "", title, flags=re.IGNORECASE).strip()

    with SessionLocal() as db:
        created = crud.create(
            db,
            models.Task,
            {
                "title": title or text,
                "priority": priority,
                "due_date": due_date,
                "status": "pendiente",
            },
        )
    await update.message.reply_text(f"Tarea creada #{created.id}: {created.title}")


async def cobro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /cobro VAXA 120000 viernes web")
        return
    client_name = context.args[0]
    try:
        amount = decimal_from_token(context.args[1])
    except InvalidOperation:
        await update.message.reply_text("No pude leer el monto.")
        return
    rest = " ".join(context.args[2:])
    due_date = parse_simple_date(rest)
    category = context.args[-1] if len(context.args) >= 4 else "otros"

    with SessionLocal() as db:
        client = crud.find_client_by_name(db, client_name)
        created = crud.create(
            db,
            models.FinanceEntry,
            {
                "type": "ingreso",
                "category": category,
                "client_id": client.id if client else None,
                "amount": amount,
                "description": f"Cobro {client_name}",
                "due_date": due_date,
                "status": "pendiente",
            },
        )
    await update.message.reply_text(f"Cobro creado #{created.id}: {format_money(created.amount)}")


async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /gasto Railway 5000 software")
        return
    description = context.args[0]
    try:
        amount = decimal_from_token(context.args[1])
    except InvalidOperation:
        await update.message.reply_text("No pude leer el monto.")
        return
    category = context.args[2] if len(context.args) >= 3 else "otros"

    with SessionLocal() as db:
        created = crud.create(
            db,
            models.FinanceEntry,
            {
                "type": "gasto",
                "category": category,
                "amount": amount,
                "description": description,
                "paid_date": date.today(),
                "status": "pagado",
            },
        )
    await update.message.reply_text(f"Gasto creado #{created.id}: {format_money(created.amount)}")


async def reunion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    if len(context.args) < 3:
        await update.message.reply_text("Uso: /reunion VAXA viernes 17 revisar web")
        return
    client_name = context.args[0]
    rest = " ".join(context.args[1:])
    meeting_date = parse_simple_date(rest) or date.today()
    hour = 9
    for token in context.args[1:]:
        if token.isdigit() and 0 <= int(token) <= 23:
            hour = int(token)
            break
    title_parts = [token for token in context.args[1:] if not token.isdigit()]
    title = " ".join(title_parts) or f"Reunion {client_name}"
    local_tz = ZoneInfo(settings.timezone)
    meeting_datetime = datetime.combine(meeting_date, time(hour=hour), tzinfo=local_tz).astimezone(UTC)

    with SessionLocal() as db:
        client = crud.find_client_by_name(db, client_name)
        created = crud.create(
            db,
            models.Meeting,
            {
                "title": f"{client_name}: {title}",
                "client_id": client.id if client else None,
                "datetime": meeting_datetime,
                "notes": rest,
                "status": "programada",
            },
        )
    await update.message.reply_text(f"Reunion creada #{created.id}: {created.title}")


async def pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    with SessionLocal() as db:
        tasks = crud.pending_tasks(db, limit=10)
        charges = crud.pending_charges(db, limit=10)
    lines = [
        "Pendientes",
        "",
        "Tareas:",
        *[f"- {task.title} ({task.priority}, {task.due_date or 'sin fecha'})" for task in tasks],
        "",
        "Cobros:",
        *[f"- {charge.description or 'Cobro'}: {format_money(charge.amount)} ({charge.status})" for charge in charges],
    ]
    await update.message.reply_text("\n".join(lines))


async def clientes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    with SessionLocal() as db:
        clients = list(
            db.scalars(select(models.Client).where(models.Client.status == "activo").order_by(models.Client.name.asc())).all()
        )
    if not clients:
        await update.message.reply_text("No hay clientes activos.")
        return
    await update.message.reply_text("\n".join(["Clientes activos", *[f"- {client.name}" for client in clients]]))


def build_application() -> Application:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to run the bot")
    if not settings.admin_telegram_id:
        raise RuntimeError("ADMIN_TELEGRAM_ID is required to run the bot")

    application = Application.builder().token(settings.telegram_bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("resumen", resumen))
    application.add_handler(CommandHandler("tarea", tarea))
    application.add_handler(CommandHandler("cobro", cobro))
    application.add_handler(CommandHandler("gasto", gasto))
    application.add_handler(CommandHandler("reunion", reunion))
    application.add_handler(CommandHandler("pendientes", pendientes))
    application.add_handler(CommandHandler("clientes", clientes))
    return application


def main() -> None:
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
