"""change moderation result category to jsonb

Revision ID: c8e4f1a7b3d2
Revises: b7c3d9e4f2a1
Create Date: 2026-08-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c8e4f1a7b3d2"
down_revision: Union[str, Sequence[str], None] = "b7c3d9e4f2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert each legacy category string into a one-element JSONB array."""
    op.alter_column(
        "moderation_results",
        "category",
        existing_type=sa.String(length=100),
        type_=postgresql.JSONB(),
        existing_nullable=False,
        postgresql_using="jsonb_build_array(category)",
    )


def downgrade() -> None:
    """Restore VARCHAR when every category value is a one-element string array."""
    # A JSONB list with multiple entries (or non-string entries) cannot be
    # faithfully represented by the original single VARCHAR column.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM moderation_results
                WHERE jsonb_typeof(category) <> 'array'
                   OR jsonb_array_length(category) <> 1
                   OR jsonb_typeof(category -> 0) <> 'string'
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade moderation_results.category to VARCHAR: '
                    'all category values must be one-element string JSON arrays';
            END IF;
        END
        $$;
        """
    )
    op.alter_column(
        "moderation_results",
        "category",
        existing_type=postgresql.JSONB(),
        type_=sa.String(length=100),
        existing_nullable=False,
        postgresql_using="category ->> 0",
    )
