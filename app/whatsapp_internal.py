from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud, models
from app.config import get_settings
from app.database import get_db
from app.whatsapp_client import is_admin_number
from app.whatsapp_parser import process_message


router = APIRouter(prefix="/internal/whatsapp", tags=["internal-whatsapp"])
settings = get_settings()


class WhatsAppMessageIn(BaseModel):
    from_number: str
    text: str
    message_id: Optional[str] = None
    timestamp: Optional[datetime | str] = None


class WhatsAppMessageOut(BaseModel):
    reply: str


def log_message(db: Session, direction: str, from_number: str, text: str, message_id: str | None, status_value: str) -> None:
    crud.create(
        db,
        models.WhatsAppMessage,
        {
            "direction": direction,
            "from_number": from_number,
            "message_id": message_id,
            "text": text,
            "status": status_value,
        },
    )


@router.post("/message", response_model=WhatsAppMessageOut)
def receive_whatsapp_message(
    payload: WhatsAppMessageIn,
    x_whatsapp_bridge_token: str = Header(default="", alias="X-Whatsapp-Bridge-Token"),
    db: Session = Depends(get_db),
):
    if not settings.whatsapp_bridge_token or x_whatsapp_bridge_token != settings.whatsapp_bridge_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bridge token")
    if not is_admin_number(payload.from_number):
        log_message(db, "incoming", payload.from_number, payload.text, payload.message_id, "unauthorized")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized WhatsApp number")

    log_message(db, "incoming", payload.from_number, payload.text, payload.message_id, "received")
    reply = process_message(db, payload.text)
    log_message(db, "outgoing", payload.from_number, reply, payload.message_id, "sent")
    return {"reply": reply}

