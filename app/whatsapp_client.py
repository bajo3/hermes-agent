from __future__ import annotations

import logging
from typing import Any

import requests

from app.config import get_settings


logger = logging.getLogger("hermes.whatsapp_client")
settings = get_settings()


def normalize_number(value: str | None) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def is_admin_number(value: str | None) -> bool:
    incoming = normalize_number(value)
    configured = normalize_number(settings.admin_whatsapp_number)
    return bool(incoming and configured and incoming == configured)


def call_windows_bridge(path: str, payload: dict[str, Any]) -> tuple[bool, str]:
    url = f"{settings.bridge_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = requests.post(
            url,
            headers={"X-Bridge-Token": settings.bridge_token},
            json=payload,
            timeout=8,
        )
    except requests.RequestException as exc:
        logger.warning("Windows bridge unavailable: %s", exc)
        return False, "Windows Bridge no esta disponible en este momento."

    if response.status_code >= 400:
        logger.warning("Windows bridge failed: %s %s", response.status_code, response.text)
        return False, f"Windows Bridge respondio con error {response.status_code}."

    try:
        data = response.json()
    except ValueError:
        data = {}
    return True, str(data.get("message") or "Comando enviado al Windows Bridge.")


def open_client_folder(client_name: str) -> str:
    ok, message = call_windows_bridge("open-folder", {"client": client_name})
    return message if ok else f"No pude abrir la carpeta de {client_name}. {message}"


def create_client_folder(client_name: str) -> str:
    ok, message = call_windows_bridge("create-folder", {"client": client_name})
    return message if ok else f"No pude crear la carpeta de {client_name}. {message}"


def save_client_note(client_name: str, note: str) -> str:
    ok, message = call_windows_bridge("note", {"client": client_name, "note": note})
    return message if ok else f"Nota guardada en Hermes. Windows Bridge: {message}"

