"""move asset relationship to moderation request

Revision ID: 1b5f3f6482a7
Revises: 3bf70e8ca0c7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1b5f3f6482a7"
down_revision: Union[str, Sequence[str], None] = "3bf70e8ca0c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new FK column first.
    op.add_column(
        "moderation_request",
        sa.Column("asset_id", sa.Uuid(), nullable=True),
    )

    op.create_index(
        "ix_moderation_request_asset_id",
        "moderation_request",
        ["asset_id"],
        unique=False,
    )

    # Preserve existing asset -> request relationships.
    op.execute(
        """
        UPDATE moderation_request AS r
        SET asset_id = a.id
        FROM moderation_assets AS a
        WHERE a.request_id = r.id
        """
    )

    op.create_foreign_key(
        "fk_moderation_request_asset_id",
        "moderation_request",
        "moderation_assets",
        ["asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Assets now belong directly to tenants.
    op.add_column(
        "moderation_assets",
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
    )

    op.create_index(
        "ix_moderation_assets_tenant_id",
        "moderation_assets",
        ["tenant_id"],
        unique=False,
    )

    # Preserve tenant ownership from the existing request.
    op.execute(
        """
        UPDATE moderation_assets AS a
        SET tenant_id = r.tenant_id
        FROM moderation_request AS r
        WHERE a.request_id = r.id
        """
    )

    # Existing assets should all have a request and therefore a tenant.
    op.alter_column(
        "moderation_assets",
        "tenant_id",
        nullable=False,
    )

    # Remove the old relationship.
    op.drop_constraint(
        "moderation_assets_request_id_fkey",
        "moderation_assets",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_moderation_assets_request_id",
        table_name="moderation_assets",
    )

    op.drop_column(
        "moderation_assets",
        "request_id",
    )


def downgrade() -> None:
    # Recreate the old relationship.
    op.add_column(
        "moderation_assets",
        sa.Column("request_id", sa.Uuid(), nullable=True),
    )

    op.create_index(
        "ix_moderation_assets_request_id",
        "moderation_assets",
        ["request_id"],
        unique=True,
    )

    op.create_foreign_key(
        "moderation_assets_request_id_fkey",
        "moderation_assets",
        "moderation_request",
        ["request_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.execute(
        """
        UPDATE moderation_assets AS a
        SET request_id = r.id
        FROM moderation_request AS r
        WHERE r.asset_id = a.id
        """
    )

    op.drop_constraint(
        "fk_moderation_request_asset_id",
        "moderation_request",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_moderation_request_asset_id",
        table_name="moderation_request",
    )

    op.drop_column(
        "moderation_request",
        "asset_id",
    )

    op.drop_index(
        "ix_moderation_assets_tenant_id",
        table_name="moderation_assets",
    )

    op.drop_column(
        "moderation_assets",
        "tenant_id",
    )