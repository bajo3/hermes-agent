from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app import models

ModelT = TypeVar("ModelT")


def _apply_updates(obj: Any, data: dict[str, Any]) -> Any:
    for key, value in data.items():
        setattr(obj, key, value)
    return obj


def create(db: Session, model: type[ModelT], data: dict[str, Any]) -> ModelT:
    obj = model(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get(db: Session, model: type[ModelT], item_id: int) -> ModelT | None:
    return db.get(model, item_id)


def list_items(db: Session, model: type[ModelT], stmt: Select[Any] | None = None) -> list[ModelT]:
    query = stmt if stmt is not None else select(model).order_by(model.id.desc())
    return list(db.scalars(query).all())


def update(db: Session, obj: ModelT, data: dict[str, Any]) -> ModelT:
    _apply_updates(obj, data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete(db: Session, obj: Any) -> None:
    db.delete(obj)
    db.commit()


def complete_task(db: Session, task: models.Task) -> models.Task:
    task.status = "completada"
    task.completed_at = datetime.now(UTC)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def mark_finance_paid(db: Session, entry: models.FinanceEntry) -> models.FinanceEntry:
    entry.status = "pagado"
    entry.paid_date = date.today()
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def find_client_by_name(db: Session, name: str) -> models.Client | None:
    return db.scalar(
        select(models.Client)
        .where(func.lower(models.Client.name).contains(name.lower()))
        .order_by(models.Client.id.asc())
    )


def month_range(today: date | None = None) -> tuple[date, date]:
    base = today or date.today()
    start = base.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def finance_summary(db: Session) -> dict[str, Decimal]:
    start, end = month_range()
    paid_this_month = models.FinanceEntry.paid_date >= start
    paid_before_next_month = models.FinanceEntry.paid_date < end
    due_this_month = models.FinanceEntry.due_date >= start
    due_before_next_month = models.FinanceEntry.due_date < end

    def total(entry_type: str, status: str | None = None, month_only: bool = False) -> Decimal:
        conditions = [models.FinanceEntry.type == entry_type]
        if status:
            conditions.append(models.FinanceEntry.status == status)
        if month_only:
            conditions.append(or_(paid_this_month & paid_before_next_month, due_this_month & due_before_next_month))
        value = db.scalar(select(func.coalesce(func.sum(models.FinanceEntry.amount), 0)).where(*conditions))
        return Decimal(value or 0)

    income_month = total("ingreso", month_only=True)
    expenses_month = total("gasto", month_only=True)
    pending_income = total("ingreso", "pendiente")
    overdue_income = total("ingreso", "vencido")
    return {
        "income_month": income_month,
        "expenses_month": expenses_month,
        "estimated_profit": income_month - expenses_month,
        "pending_income": pending_income,
        "overdue_income": overdue_income,
    }


def upcoming_meetings(db: Session, limit: int = 5) -> list[models.Meeting]:
    now = datetime.now(UTC)
    return list(
        db.scalars(
            select(models.Meeting)
            .where(models.Meeting.datetime >= now, models.Meeting.status != "cancelada")
            .order_by(models.Meeting.datetime.asc())
            .limit(limit)
        ).all()
    )


def pending_tasks(db: Session, limit: int | None = None) -> list[models.Task]:
    stmt = (
        select(models.Task)
        .where(models.Task.status.in_(["pendiente", "en_progreso"]))
        .order_by(models.Task.due_date.asc().nullslast(), models.Task.priority.desc(), models.Task.id.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def pending_charges(db: Session, limit: int | None = None) -> list[models.FinanceEntry]:
    stmt = (
        select(models.FinanceEntry)
        .where(models.FinanceEntry.type == "ingreso", models.FinanceEntry.status.in_(["pendiente", "vencido"]))
        .order_by(models.FinanceEntry.due_date.asc().nullslast(), models.FinanceEntry.id.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def active_projects(db: Session) -> list[models.Project]:
    return list(
        db.scalars(
            select(models.Project)
            .where(models.Project.status.in_(["pendiente", "en_progreso", "esperando_cliente"]))
            .order_by(models.Project.due_date.asc().nullslast(), models.Project.id.desc())
        ).all()
    )


def dashboard_stats(db: Session) -> dict[str, Any]:
    summary = finance_summary(db)
    return {
        **summary,
        "pending_tasks": pending_tasks(db, limit=8),
        "upcoming_meetings": upcoming_meetings(db, limit=8),
        "pending_charges": pending_charges(db, limit=8),
        "active_projects_count": db.scalar(
            select(func.count()).select_from(models.Project).where(models.Project.status.in_(["pendiente", "en_progreso", "esperando_cliente"]))
        )
        or 0,
        "active_clients_count": db.scalar(
            select(func.count()).select_from(models.Client).where(models.Client.status == "activo")
        )
        or 0,
    }


def due_today_window() -> tuple[datetime, datetime]:
    today = date.today()
    return datetime.combine(today, time.min).replace(tzinfo=UTC), datetime.combine(today, time.max).replace(tzinfo=UTC)


def reminders_to_send(db: Session) -> list[models.Reminder]:
    return list(
        db.scalars(
            select(models.Reminder)
            .where(models.Reminder.sent.is_(False), models.Reminder.remind_at <= datetime.now(UTC))
            .order_by(models.Reminder.remind_at.asc())
        ).all()
    )


def mark_overdue_charges(db: Session) -> list[models.FinanceEntry]:
    today = date.today()
    entries = list(
        db.scalars(
            select(models.FinanceEntry).where(
                models.FinanceEntry.type == "ingreso",
                models.FinanceEntry.status == "pendiente",
                models.FinanceEntry.due_date.is_not(None),
                models.FinanceEntry.due_date < today,
            )
        ).all()
    )
    for entry in entries:
        entry.status = "vencido"
        db.add(entry)
    db.commit()
    return entries


def items_for_today(db: Session) -> dict[str, Any]:
    today = date.today()
    start_dt, end_dt = due_today_window()
    return {
        "tasks": list(
            db.scalars(
                select(models.Task)
                .where(models.Task.status.in_(["pendiente", "en_progreso"]), models.Task.due_date == today)
                .order_by(models.Task.priority.desc(), models.Task.id.desc())
            ).all()
        ),
        "meetings": list(
            db.scalars(
                select(models.Meeting)
                .where(models.Meeting.datetime >= start_dt, models.Meeting.datetime <= end_dt, models.Meeting.status != "cancelada")
                .order_by(models.Meeting.datetime.asc())
            ).all()
        ),
        "overdue_projects": list(
            db.scalars(
                select(models.Project)
                .where(
                    models.Project.status.in_(["pendiente", "en_progreso", "esperando_cliente"]),
                    models.Project.due_date.is_not(None),
                    models.Project.due_date < today,
                )
                .order_by(models.Project.due_date.asc())
            ).all()
        ),
        "pending_charges": pending_charges(db, limit=10),
        "summary": finance_summary(db),
    }

