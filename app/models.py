from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(80))
    email: Mapped[Optional[str]] = mapped_column(String(160))
    company: Mapped[Optional[str]] = mapped_column(String(160))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="activo", index=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="client")
    tasks: Mapped[list["Task"]] = relationship(back_populates="client")
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="client")
    finance_entries: Mapped[list["FinanceEntry"]] = relationship(back_populates="client")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="pendiente", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="media", index=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    due_date: Mapped[Optional[date]] = mapped_column(Date)

    client: Mapped["Client"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")
    finance_entries: Mapped[list["FinanceEntry"]] = relationship(back_populates="project")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="pendiente", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="media", index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    client: Mapped[Optional["Client"]] = relationship(back_populates="tasks")
    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")


class Meeting(Base, TimestampMixin):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), index=True)
    datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    location: Mapped[Optional[str]] = mapped_column(String(220))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="programada", index=True)

    client: Mapped[Optional["Client"]] = relationship(back_populates="meetings")


class FinanceEntry(Base, TimestampMixin):
    __tablename__ = "finance_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), default="otros", index=True)
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    paid_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="pendiente", index=True)

    client: Mapped[Optional["Client"]] = relationship(back_populates="finance_entries")
    project: Mapped[Optional["Project"]] = relationship(back_populates="finance_entries")


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sent: Mapped[bool] = mapped_column(default=False, index=True)
    related_type: Mapped[Optional[str]] = mapped_column(String(80))
    related_id: Mapped[Optional[int]] = mapped_column(index=True)


class WhatsAppMessage(Base, TimestampMixin):
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    from_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    message_id: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="processed", index=True)
