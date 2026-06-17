from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db


router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_model=list[schemas.MeetingRead])
def list_meetings(db: Session = Depends(get_db)):
    return crud.list_items(db, models.Meeting)


@router.post("", response_model=schemas.MeetingRead, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: schemas.MeetingCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if data.get("client_id") and not crud.get(db, models.Client, data["client_id"]):
        raise HTTPException(status_code=400, detail="client_id does not exist")
    return crud.create(db, models.Meeting, data)


@router.get("/{meeting_id}", response_model=schemas.MeetingRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = crud.get(db, models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.put("/{meeting_id}", response_model=schemas.MeetingRead)
def update_meeting(meeting_id: int, payload: schemas.MeetingUpdate, db: Session = Depends(get_db)):
    meeting = crud.get(db, models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("client_id") and not crud.get(db, models.Client, data["client_id"]):
        raise HTTPException(status_code=400, detail="client_id does not exist")
    return crud.update(db, meeting, data)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = crud.get(db, models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    crud.delete(db, meeting)
    return None

