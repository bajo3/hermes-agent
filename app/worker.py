import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, Update

from app import crud
from app.config import get_settings
from app.database import SessionLocal
from app.telegram_bot import build_application, format_money


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("hermes.worker")
settings = get_settings()


async def send_admin_message(bot: Bot, text: str) -> None:
    if settings.admin_telegram_id:
        await bot.send_message(chat_id=settings.admin_telegram_id, text=text)


async def process_tick(bot: Bot | None = None) -> None:
    with SessionLocal() as db:
        overdue = crud.mark_overdue_charges(db)
        reminders = crud.reminders_to_send(db)
        for reminder in reminders:
            reminder.sent = True
            db.add(reminder)
        db.commit()

    if bot and overdue:
        lines = ["Cobros marcados como vencidos:"]
        lines.extend(f"- {entry.description or 'Cobro'}: {format_money(entry.amount)}" for entry in overdue)
        await send_admin_message(bot, "\n".join(lines))

    if bot:
        for reminder in reminders:
            await send_admin_message(bot, f"Recordatorio: {reminder.title}\n{reminder.description or ''}".strip())

    logger.info("Worker tick complete: overdue=%s reminders=%s", len(overdue), len(reminders))


async def run() -> None:
    application = None
    bot = None
    if settings.telegram_bot_token and settings.admin_telegram_id:
        application = build_application()
        bot = application.bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Telegram bot polling started")
    else:
        logger.warning("Telegram bot disabled: configure TELEGRAM_BOT_TOKEN and ADMIN_TELEGRAM_ID")

    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(process_tick, "interval", seconds=60, args=[bot], id="worker_tick", max_instances=1)
    scheduler.start()
    await process_tick(bot)
    logger.info("Worker scheduler started")

    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)
        if application:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()

