"""repair outbox claim token schema drift

Revision ID: 9123382f79d2
Revises: d29e6a1f4b08
Create Date: 2026-10-12 00:48:28.731190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9123382f79d2'
down_revision: Union[str, Sequence[str], None] = "d29e6a1f4b08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE outbox_events "
        "ADD COLUMN IF NOT EXISTS claim_token UUID"
    )


def downgrade() -> None:
    # Intentional no-op: this migration repairs possible schema drift
    # and must not remove a column that may have existed beforehand.
    pass