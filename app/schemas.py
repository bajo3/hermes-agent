from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ClientBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    status: str = "activo"


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class ClientRead(ClientBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class ProjectBase(BaseModel):
    client_id: int
    name: str
    description: Optional[str] = None
    status: str = "pendiente"
    priority: str = "media"
    price: Optional[Decimal] = None
    due_date: Optional[date] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    client_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    price: Optional[Decimal] = None
    due_date: Optional[date] = None


class ProjectRead(ProjectBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    status: str = "pendiente"
    priority: str = "media"
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None


class TaskRead(TaskBase, ORMModel):
    id: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MeetingBase(BaseModel):
    title: str
    client_id: Optional[int] = None
    datetime: datetime
    location: Optional[str] = None
    notes: Optional[str] = None
    status: str = "programada"


class MeetingCreate(MeetingBase):
    pass


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    client_id: Optional[int] = None
    datetime: Optional[datetime] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class MeetingRead(MeetingBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class FinanceEntryBase(BaseModel):
    type: str
    category: str = "otros"
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    amount: Decimal
    description: Optional[str] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    status: str = "pendiente"


class FinanceEntryCreate(FinanceEntryBase):
    pass


class FinanceEntryUpdate(BaseModel):
    type: Optional[str] = None
    category: Optional[str] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    status: Optional[str] = None


class FinanceEntryRead(FinanceEntryBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class FinanceSummary(BaseModel):
    income_month: Decimal
    expenses_month: Decimal
    estimated_profit: Decimal
    pending_income: Decimal
    overdue_income: Decimal


class ReminderBase(BaseModel):
    title: str
    description: Optional[str] = None
    remind_at: datetime
    sent: bool = False
    related_type: Optional[str] = None
    related_id: Optional[int] = None


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    remind_at: Optional[datetime] = None
    sent: Optional[bool] = None
    related_type: Optional[str] = None
    related_id: Optional[int] = None


class ReminderRead(ReminderBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime

