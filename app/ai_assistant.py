from __future__ import annotations

import json
import logging
from datetime import date
from typing import Callable

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models
from app.config import get_settings


logger = logging.getLogger("hermes.ai")
settings = get_settings()


SYSTEM_PROMPT = """
Sos Hermes Secretario, un asistente operativo por WhatsApp para finanzas, clientes, proyectos, tareas y reuniones.
Tu trabajo es convertir mensajes naturales en un comando interno de Hermes cuando sea posible.
No inventes datos. Si falta un dato imprescindible, pedilo en una frase breve.

Comandos internos disponibles:
- ayuda
- resumen
- pendientes
- clientes
- proyectos
- tarea <titulo> para <fecha opcional> prioridad <baja|media|alta|urgente>
- cobro <cliente> <monto> <fecha opcional> <categoria opcional>
- gasto <descripcion> <monto> <categoria opcional>
- reunion <cliente> <fecha> <hora opcional> <motivo>
- abrir carpeta <cliente>
- crear carpeta <cliente>
- nota <cliente> <nota>

Devolve solo JSON valido con esta forma:
{
  "mode": "command" | "reply",
  "command": "comando interno o null",
  "reply": "respuesta breve si mode=reply o null"
}
"""


def ai_available() -> bool:
    return bool(settings.ai_enabled and settings.openai_api_key)


def context_snapshot(db: Session) -> str:
    clients = list(
        db.scalars(select(models.Client).where(models.Client.status == "activo").order_by(models.Client.name.asc()).limit(20)).all()
    )
    projects = crud.active_projects(db)[:10]
    tasks = crud.pending_tasks(db, limit=10)
    charges = crud.pending_charges(db, limit=10)
    summary = crud.finance_summary(db)

    return "\n".join(
        [
            f"Fecha actual: {date.today().isoformat()}",
            "Clientes activos: " + (", ".join(client.name for client in clients) if clients else "ninguno"),
            "Proyectos activos: " + (", ".join(project.name for project in projects) if projects else "ninguno"),
            "Tareas pendientes: " + (", ".join(task.title for task in tasks) if tasks else "ninguna"),
            "Cobros pendientes: " + (", ".join(charge.description or "Cobro" for charge in charges) if charges else "ninguno"),
            f"Ingresos del mes: {summary['income_month']}",
            f"Gastos del mes: {summary['expenses_month']}",
        ]
    )


def parse_ai_json(raw: str) -> dict[str, str | None]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    data = json.loads(cleaned)
    return {
        "mode": data.get("mode"),
        "command": data.get("command"),
        "reply": data.get("reply"),
    }


def interpret_with_ai(db: Session, text: str, execute_command: Callable[[str], str]) -> str | None:
    if not ai_available():
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = "\n\n".join(
        [
            "Contexto actual de Hermes:",
            context_snapshot(db),
            "Mensaje recibido por WhatsApp:",
            text,
        ]
    )

    try:
        response = client.responses.create(
            model=settings.openai_model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
            max_output_tokens=500,
        )
        decision = parse_ai_json(response.output_text)
    except Exception as exc:
        logger.warning("OpenAI interpretation failed: %s", exc)
        if "insufficient_quota" in str(exc) or "exceeded your current quota" in str(exc):
            return "La IA esta configurada, pero la API de OpenAI no tiene cuota disponible. Revisa billing/credits en platform.openai.com."
        return "No pude usar la IA ahora. Proba con un comando directo como ayuda, resumen o tarea ..."

    mode = decision.get("mode")
    command = (decision.get("command") or "").strip()
    reply = (decision.get("reply") or "").strip()

    if mode == "command" and command:
        return execute_command(command)
    if reply:
        return reply
    return "No entendi bien. Escribi ayuda para ver comandos o mandame la instruccion con un poco mas de detalle."
