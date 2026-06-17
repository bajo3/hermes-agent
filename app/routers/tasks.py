from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db


router = APIRouter(prefix="/tasks", tags=["tasks"])


def _validate_links(db: Session, data: dict) -> None:
    if data.get("client_id") and not crud.get(db, models.Client, data["client_id"]):
        raise HTTPException(status_code=400, detail="client_id does not exist")
    if data.get("project_id") and not crud.get(db, models.Project, data["project_id"]):
        raise HTTPException(status_code=400, detail="project_id does not exist")


@router.get("", response_model=list[schemas.TaskRead])
def list_tasks(db: Session = Depends(get_db)):
    return crud.list_items(db, models.Task)


@router.post("", response_model=schemas.TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    _validate_links(db, data)
    return crud.create(db, models.Task, data)


@router.get("/{task_id}", response_model=schemas.TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get(db, models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=schemas.TaskRead)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = crud.get(db, models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    data = payload.model_dump(exclude_unset=True)
    _validate_links(db, data)
    return crud.update(db, task, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get(db, models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    crud.delete(db, task)
    return None


@router.post("/{task_id}/complete", response_model=schemas.TaskRead)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get(db, models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return crud.complete_task(db, task)

