"""harden_outbox_events_table

Revision ID: c870dd462f24
Revises: dc136d9e33be
Create Date: 2026-10-06 19:50:33.159285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c870dd462f24'
down_revision: Union[str, Sequence[str], None] = 'dc136d9e33be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'outbox_events',
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'outbox_events',
        sa.Column('claim_token', sa.Uuid(), nullable=True),
    )
    op.add_column(
        'outbox_events',
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'outbox_events',
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'outbox_events',
        sa.Column('last_error', sa.Text(), nullable=True),
    )
    op.create_index(
        'ix_outbox_events_status_created_at',
        'outbox_events',
        ['status', 'created_at'],
    )
    op.create_index(
        'ix_outbox_events_status_claimed_at',
        'outbox_events',
        ['status', 'claimed_at'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_outbox_events_status_claimed_at', table_name='outbox_events')
    op.drop_index('ix_outbox_events_status_created_at', table_name='outbox_events')
    op.drop_column('outbox_events', 'last_error')
    op.drop_column('outbox_events', 'attempts')
    op.drop_column('outbox_events', 'published_at')
    op.drop_column('outbox_events', 'claim_token')
    op.drop_column('outbox_events', 'claimed_at')
