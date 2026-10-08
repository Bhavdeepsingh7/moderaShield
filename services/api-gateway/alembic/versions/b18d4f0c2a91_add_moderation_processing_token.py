"""add a durable moderation processing claim

Revision ID: b18d4f0c2a91
Revises: c870dd462f24
Create Date: 2026-10-09 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b18d4f0c2a91"
down_revision: Union[str, Sequence[str], None] = "c870dd462f24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("moderation_request", sa.Column("processing_token", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_moderation_request_processing_token"), "moderation_request", ["processing_token"])


def downgrade() -> None:
    op.drop_index(op.f("ix_moderation_request_processing_token"), table_name="moderation_request")
    op.drop_column("moderation_request", "processing_token")
