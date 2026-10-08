"""harden webhook delivery claims and uniqueness

Revision ID: d29e6a1f4b08
Revises: b18d4f0c2a91
"""
from alembic import op
import sqlalchemy as sa

revision = "d29e6a1f4b08"
down_revision = "b18d4f0c2a91"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("webhook_deliveries", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("webhook_deliveries", sa.Column("claim_token", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_webhook_deliveries_claimed_at"), "webhook_deliveries", ["claimed_at"])
    op.create_index(op.f("ix_webhook_deliveries_claim_token"), "webhook_deliveries", ["claim_token"])
    op.create_unique_constraint("uq_webhook_delivery_logical_event", "webhook_deliveries", ["webhook_id", "request_id", "event_type"])

def downgrade() -> None:
    op.drop_constraint("uq_webhook_delivery_logical_event", "webhook_deliveries", type_="unique")
    op.drop_index(op.f("ix_webhook_deliveries_claim_token"), table_name="webhook_deliveries")
    op.drop_index(op.f("ix_webhook_deliveries_claimed_at"), table_name="webhook_deliveries")
    op.drop_column("webhook_deliveries", "claim_token")
    op.drop_column("webhook_deliveries", "claimed_at")
