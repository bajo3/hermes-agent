"""whatsapp messages

Revision ID: 20260617_0002
Revises: 20260617_0001
Create Date: 2026-06-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260617_0002"
down_revision: str | None = "20260617_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("from_number", sa.String(length=40), nullable=False),
        sa.Column("message_id", sa.String(length=120), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_whatsapp_messages_direction"), "whatsapp_messages", ["direction"], unique=False)
    op.create_index(op.f("ix_whatsapp_messages_from_number"), "whatsapp_messages", ["from_number"], unique=False)
    op.create_index(op.f("ix_whatsapp_messages_id"), "whatsapp_messages", ["id"], unique=False)
    op.create_index(op.f("ix_whatsapp_messages_message_id"), "whatsapp_messages", ["message_id"], unique=False)
    op.create_index(op.f("ix_whatsapp_messages_status"), "whatsapp_messages", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("whatsapp_messages")

