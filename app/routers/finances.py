from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db


router = APIRouter(prefix="/finances", tags=["finances"])


def _validate_links(db: Session, data: dict) -> None:
    if data.get("client_id") and not crud.get(db, models.Client, data["client_id"]):
        raise HTTPException(status_code=400, detail="client_id does not exist")
    if data.get("project_id") and not crud.get(db, models.Project, data["project_id"]):
        raise HTTPException(status_code=400, detail="project_id does not exist")


@router.get("", response_model=list[schemas.FinanceEntryRead])
def list_finances(db: Session = Depends(get_db)):
    return crud.list_items(db, models.FinanceEntry)


@router.post("", response_model=schemas.FinanceEntryRead, status_code=status.HTTP_201_CREATED)
def create_finance(payload: schemas.FinanceEntryCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    _validate_links(db, data)
    return crud.create(db, models.FinanceEntry, data)


@router.get("/summary", response_model=schemas.FinanceSummary)
def get_summary(db: Session = Depends(get_db)):
    return crud.finance_summary(db)


@router.get("/pending", response_model=list[schemas.FinanceEntryRead])
def get_pending(db: Session = Depends(get_db)):
    stmt = (
        select(models.FinanceEntry)
        .where(models.FinanceEntry.status.in_(["pendiente", "vencido"]))
        .order_by(models.FinanceEntry.due_date.asc().nullslast(), models.FinanceEntry.id.desc())
    )
    return crud.list_items(db, models.FinanceEntry, stmt)


@router.put("/{finance_id}", response_model=schemas.FinanceEntryRead)
def update_finance(finance_id: int, payload: schemas.FinanceEntryUpdate, db: Session = Depends(get_db)):
    entry = crud.get(db, models.FinanceEntry, finance_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Finance entry not found")
    data = payload.model_dump(exclude_unset=True)
    _validate_links(db, data)
    return crud.update(db, entry, data)


@router.delete("/{finance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_finance(finance_id: int, db: Session = Depends(get_db)):
    entry = crud.get(db, models.FinanceEntry, finance_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Finance entry not found")
    crud.delete(db, entry)
    return None


@router.post("/{finance_id}/mark-paid", response_model=schemas.FinanceEntryRead)
def mark_paid(finance_id: int, db: Session = Depends(get_db)):
    entry = crud.get(db, models.FinanceEntry, finance_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Finance entry not found")
    return crud.mark_finance_paid(db, entry)

