from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[schemas.ClientRead])
def list_clients(db: Session = Depends(get_db)):
    return crud.list_items(db, models.Client)


@router.post("", response_model=schemas.ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(payload: schemas.ClientCreate, db: Session = Depends(get_db)):
    return crud.create(db, models.Client, payload.model_dump())


@router.get("/{client_id}", response_model=schemas.ClientRead)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = crud.get(db, models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=schemas.ClientRead)
def update_client(client_id: int, payload: schemas.ClientUpdate, db: Session = Depends(get_db)):
    client = crud.get(db, models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return crud.update(db, client, payload.model_dump(exclude_unset=True))


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = crud.get(db, models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    crud.delete(db, client)
    return None

