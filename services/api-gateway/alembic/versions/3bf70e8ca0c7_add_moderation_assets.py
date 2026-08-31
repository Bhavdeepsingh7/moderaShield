"""add moderation assets

Revision ID: 3bf70e8ca0c7
Revises: 9823ae891a21
Create Date: 2026-08-28 23:00:30.464410

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3bf70e8ca0c7"
down_revision: Union[str, Sequence[str], None] = "9823ae891a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "moderation_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("storage_provider", sa.String(length=50), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("asset_metadata", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["moderation_request.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_moderation_assets_request_id"),
        "moderation_assets",
        ["request_id"],
        unique=True,
    )

    op.alter_column(
        "moderation_request",
        "content",
        existing_type=sa.TEXT(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "moderation_request",
        "content",
        existing_type=sa.TEXT(),
        nullable=False,
    )

    op.drop_index(
        op.f("ix_moderation_assets_request_id"),
        table_name="moderation_assets",
    )

    op.drop_table("moderation_assets")