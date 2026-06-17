from __future__ import annotations

import json
import logging
import shlex
import subprocess
import urllib.error
import urllib.request
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
    if not settings.ai_enabled:
        return False
    if settings.ai_provider == "openai":
        return bool(settings.openai_api_key)
    if settings.ai_provider in {"hermes_cli", "hermes_http"}:
        return True
    return False


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


def build_prompt(db: Session, text: str) -> str:
    return "\n\n".join(
        [
            SYSTEM_PROMPT.strip(),
            "Contexto actual de Hermes:",
            context_snapshot(db),
            "Mensaje recibido por WhatsApp:",
            text,
        ]
    )


def interpret_with_openai(prompt: str) -> dict[str, str | None]:
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        instructions=SYSTEM_PROMPT,
        input=prompt,
        max_output_tokens=500,
    )
    return parse_ai_json(response.output_text)


def hermes_cli_command(prompt: str) -> list[str]:
    if settings.hermes_cli_command:
        command = shlex.split(settings.hermes_cli_command)
    else:
        command = [settings.hermes_cli_path]
    command.extend(
        [
            "-z",
            prompt,
            "--provider",
            settings.hermes_cli_provider,
            "--model",
            settings.hermes_cli_model,
        ]
    )
    return command


def interpret_with_hermes_cli(prompt: str) -> dict[str, str | None]:
    result = subprocess.run(
        hermes_cli_command(prompt),
        cwd=settings.hermes_cli_cwd or None,
        text=True,
        capture_output=True,
        timeout=settings.hermes_cli_timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Hermes CLI failed").strip())
    return parse_ai_json(result.stdout)


def interpret_with_hermes_http(prompt: str) -> dict[str, str | None]:
    payload = json.dumps(
        {
            "prompt": prompt,
            "provider": settings.hermes_cli_provider,
            "model": settings.hermes_cli_model,
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.hermes_cli_bridge_token:
        headers["Authorization"] = f"Bearer {settings.hermes_cli_bridge_token}"
    request = urllib.request.Request(settings.hermes_cli_bridge_url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=settings.hermes_cli_timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if data.get("error"):
        raise RuntimeError(data["error"])
    return parse_ai_json(data.get("output", ""))


def run_ai_interpretation(prompt: str) -> dict[str, str | None]:
    if settings.ai_provider == "openai":
        return interpret_with_openai(prompt)
    if settings.ai_provider == "hermes_cli":
        return interpret_with_hermes_cli(prompt)
    if settings.ai_provider == "hermes_http":
        return interpret_with_hermes_http(prompt)
    raise RuntimeError(f"Proveedor de IA no soportado: {settings.ai_provider}")


def apply_ai_decision(decision: dict[str, str | None], execute_command: Callable[[str], str]) -> str:
    mode = decision.get("mode")
    command = (decision.get("command") or "").strip()
    reply = (decision.get("reply") or "").strip()

    if mode == "command" and command:
        return execute_command(command)
    if reply:
        return reply
    return "No entendi bien. Escribi ayuda para ver comandos o mandame la instruccion con un poco mas de detalle."


def interpret_with_ai(db: Session, text: str, execute_command: Callable[[str], str]) -> str | None:
    if not ai_available():
        return None

    prompt = build_prompt(db, text)
    try:
        decision = run_ai_interpretation(prompt)
    except Exception as exc:
        logger.warning("%s interpretation failed: %s", settings.ai_provider, exc)
        if "insufficient_quota" in str(exc) or "exceeded your current quota" in str(exc):
            return "La IA esta configurada, pero la API de OpenAI no tiene cuota disponible. Revisa billing/credits en platform.openai.com."
        if isinstance(exc, urllib.error.URLError):
            return "No pude conectar con el puente local de Hermes. Verifica que este corriendo en WSL."
        return "No pude usar la IA ahora. Proba con un comando directo como ayuda, resumen o tarea ..."

    return apply_ai_decision(decision, execute_command)
