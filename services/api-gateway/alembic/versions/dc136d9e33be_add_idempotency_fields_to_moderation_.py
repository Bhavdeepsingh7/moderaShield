"""add_idempotency_fields_to_moderation_request

Revision ID: dc136d9e33be
Revises: 1b5f3f6482a7
Create Date: 2026-10-06 19:23:17.708836

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc136d9e33be'
down_revision: Union[str, Sequence[str], None] = '1b5f3f6482a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'moderation_request',
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'moderation_request',
        sa.Column('request_hash', sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        'uq_moderation_request_tenant_idempotency_key',
        'moderation_request',
        ['tenant_id', 'idempotency_key'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'uq_moderation_request_tenant_idempotency_key',
        'moderation_request',
        type_='unique',
    )
    op.drop_column('moderation_request', 'request_hash')
    op.drop_column('moderation_request', 'idempotency_key')

