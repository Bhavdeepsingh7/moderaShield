"""create outbox events table

Revision ID: 41a61a8cddaf
Revises: 67ea4743e8f8
Create Date: 2026-08-11 19:39:40.247076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41a61a8cddaf'
down_revision: Union[str, Sequence[str], None] = '67ea4743e8f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_outbox_events_aggregate_id",
        "outbox_events",
        ["aggregate_id"],
        unique=False,
    )

    op.create_index(
        "ix_outbox_events_status",
        "outbox_events",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outbox_events_status",
        table_name="outbox_events",
    )

    op.drop_index(
        "ix_outbox_events_aggregate_id",
        table_name="outbox_events",
    )

    op.drop_table("outbox_events")