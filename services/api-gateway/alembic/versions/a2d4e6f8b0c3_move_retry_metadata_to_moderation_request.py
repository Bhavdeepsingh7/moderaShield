"""move retry metadata to moderation request

Revision ID: a2d4e6f8b0c3
Revises: c8e4f1a7b3d2
"""

from alembic import op
import sqlalchemy as sa


revision = "a2d4e6f8b0c3"
down_revision = "c8e4f1a7b3d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Failed jobs have no moderation_result, so retry state must live here.
    op.add_column(
        "moderation_request",
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("moderation_request", sa.Column("last_error", sa.Text(), nullable=True))
    op.drop_column("moderation_results", "last_error")
    op.drop_column("moderation_results", "retry_count")


def downgrade() -> None:
    op.add_column(
        "moderation_results",
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("moderation_results", sa.Column("last_error", sa.Text(), nullable=True))
    op.drop_column("moderation_request", "last_error")
    op.drop_column("moderation_request", "retry_count")
