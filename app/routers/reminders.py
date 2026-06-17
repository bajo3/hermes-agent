from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db


router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[schemas.ReminderRead])
def list_reminders(db: Session = Depends(get_db)):
    return crud.list_items(db, models.Reminder)


@router.post("", response_model=schemas.ReminderRead, status_code=status.HTTP_201_CREATED)
def create_reminder(payload: schemas.ReminderCreate, db: Session = Depends(get_db)):
    return crud.create(db, models.Reminder, payload.model_dump())


@router.put("/{reminder_id}", response_model=schemas.ReminderRead)
def update_reminder(reminder_id: int, payload: schemas.ReminderUpdate, db: Session = Depends(get_db)):
    reminder = crud.get(db, models.Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return crud.update(db, reminder, payload.model_dump(exclude_unset=True))


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    reminder = crud.get(db, models.Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    crud.delete(db, reminder)
    return None

