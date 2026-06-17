import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from telegram import Bot

from app import crud
from app.config import get_settings
from app.database import SessionLocal
from app.telegram_bot import format_money


settings = get_settings()


def _lines_for_amounts(summary: dict[str, Decimal]) -> list[str]:
    return [
        f"Ingresos del mes: {format_money(summary['income_month'])}",
        f"Gastos del mes: {format_money(summary['expenses_month'])}",
        f"Ganancia estimada: {format_money(summary['estimated_profit'])}",
    ]


def build_daily_summary() -> str:
    with SessionLocal() as db:
        data = crud.items_for_today(db)

    lines = [
        f"Resumen diario Hermes - {datetime.now(UTC).strftime('%d/%m/%Y')}",
        "",
        "Tareas del dia:",
        *[f"- {task.title} ({task.priority})" for task in data["tasks"]],
        "" if data["tasks"] else "- Sin tareas para hoy",
        "",
        "Reuniones del dia:",
        *[f"- {meeting.title} ({meeting.datetime.strftime('%H:%M')})" for meeting in data["meetings"]],
        "" if data["meetings"] else "- Sin reuniones para hoy",
        "",
        "Cobros pendientes:",
        *[f"- {entry.description or 'Cobro'}: {format_money(entry.amount)} ({entry.status})" for entry in data["pending_charges"]],
        "" if data["pending_charges"] else "- Sin cobros pendientes",
        "",
        "Trabajos atrasados:",
        *[f"- {project.name} (vence {project.due_date})" for project in data["overdue_projects"]],
        "" if data["overdue_projects"] else "- Sin trabajos atrasados",
        "",
        *_lines_for_amounts(data["summary"]),
    ]
    return "\n".join(line for line in lines if line is not None)


async def send_daily_summary() -> None:
    if not settings.telegram_bot_token or not settings.admin_telegram_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and ADMIN_TELEGRAM_ID are required")
    bot = Bot(settings.telegram_bot_token)
    await bot.send_message(chat_id=settings.admin_telegram_id, text=build_daily_summary())


def main() -> None:
    asyncio.run(send_daily_summary())


if __name__ == "__main__":
    main()

