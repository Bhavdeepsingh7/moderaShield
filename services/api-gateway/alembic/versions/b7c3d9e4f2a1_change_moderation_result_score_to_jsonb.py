"""change moderation result score to jsonb

Revision ID: b7c3d9e4f2a1
Revises: f979a8d1d671
Create Date: 2026-08-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b7c3d9e4f2a1"
down_revision: Union[str, Sequence[str], None] = "f979a8d1d671"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store scores as JSONB, preserving existing numeric scores as JSON numbers."""
    op.alter_column(
        "moderation_results",
        "score",
        existing_type=sa.Float(),
        type_=postgresql.JSONB(),
        existing_nullable=False,
        postgresql_using="to_jsonb(score)",
    )


def downgrade() -> None:
    """Restore double precision when every JSONB score is a numeric JSON scalar."""
    # JSON objects/arrays cannot be faithfully represented as a double precision
    # value. Fail explicitly rather than silently discarding score data.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM moderation_results
                WHERE jsonb_typeof(score) <> 'number'
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade moderation_results.score to double precision: '
                    'all score values must be numeric JSON scalars';
            END IF;
        END
        $$;
        """
    )
    op.alter_column(
        "moderation_results",
        "score",
        existing_type=postgresql.JSONB(),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using="(score #>> '{}')::double precision",
    )
