from __future__ import annotations

import logging
from typing import Any

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models
from app.config import get_settings
from app.database import get_db
from app.telegram_bot import format_money


logger = logging.getLogger("hermes.whatsapp")
router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])
settings = get_settings()


def normalize_phone(value: str | None) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def is_admin_phone(phone: str | None) -> bool:
    configured = normalize_phone(settings.admin_whatsapp_phone)
    incoming = normalize_phone(phone)
    return bool(configured and incoming and configured == incoming)


def send_whatsapp_message(to_phone: str, text: str) -> None:
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        logger.warning("WhatsApp send skipped: missing access token or phone number id")
        return

    url = f"https://graph.facebook.com/v20.0/{settings.whatsapp_phone_number_id}/messages"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        },
        json={
            "messaging_product": "whatsapp",
            "to": normalize_phone(to_phone),
            "type": "text",
            "text": {"preview_url": False, "body": text[:3900]},
        },
        timeout=15,
    )
    if response.status_code >= 400:
        logger.error("WhatsApp send failed: %s %s", response.status_code, response.text)


def build_resumen(db: Session) -> str:
    summary = crud.finance_summary(db)
    tasks = crud.pending_tasks(db, limit=5)
    charges = crud.pending_charges(db, limit=5)
    meetings = crud.upcoming_meetings(db, limit=5)
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


def build_pendientes(db: Session) -> str:
    tasks = crud.pending_tasks(db, limit=10)
    charges = crud.pending_charges(db, limit=10)
    lines = [
        "Pendientes",
        "",
        "Tareas:",
        *[f"- {task.title} ({task.priority}, {task.due_date or 'sin fecha'})" for task in tasks],
        "",
        "Cobros:",
        *[f"- {entry.description or 'Cobro'}: {format_money(entry.amount)} ({entry.status})" for entry in charges],
    ]
    return "\n".join(lines)


def build_clientes(db: Session) -> str:
    clients = list(
        db.scalars(select(models.Client).where(models.Client.status == "activo").order_by(models.Client.name.asc())).all()
    )
    if not clients:
        return "No hay clientes activos."
    return "\n".join(["Clientes activos", *[f"- {client.name}" for client in clients]])


def handle_text_message(db: Session, text: str) -> str:
    command = text.strip()
    command_lower = command.lower()
    if command_lower in {"hola", "ayuda", "start", "/start"}:
        return "\n".join(
            [
                "Hermes Secretario listo por WhatsApp.",
                "",
                "Comandos:",
                "resumen",
                "pendientes",
                "clientes",
            ]
        )
    if command_lower in {"resumen", "/resumen"}:
        return build_resumen(db)
    if command_lower in {"pendientes", "/pendientes"}:
        return build_pendientes(db)
    if command_lower in {"clientes", "/clientes"}:
        return build_clientes(db)
    return "Comando no reconocido. Proba con: resumen, pendientes o clientes."


def extract_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                messages.append(message)
    return messages


@router.get("")
def verify_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    if mode == "subscribe" and token and token == settings.whatsapp_verify_token:
        return PlainTextResponse(challenge or "")
    raise HTTPException(status_code=403, detail="Invalid WhatsApp verify token")


@router.post("")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    for message in extract_messages(payload):
        from_phone = message.get("from")
        if not is_admin_phone(from_phone):
            logger.info("Ignoring WhatsApp message from unauthorized phone: %s", from_phone)
            continue
        if message.get("type") != "text":
            send_whatsapp_message(from_phone, "Por ahora Hermes solo procesa texto.")
            continue
        incoming_text = message.get("text", {}).get("body", "")
        response = handle_text_message(db, incoming_text)
        send_whatsapp_message(from_phone, response)
    return {"status": "ok"}
