"""create webhooks and webhook deliveries tables

Revision ID: 9823ae891a21
Revises: a2d4e6f8b0c3
Create Date: 2026-08-27 15:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9823ae891a21'
down_revision: Union[str, Sequence[str], None] = 'a2d4e6f8b0c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhooks_tenant_id'), 'webhooks', ['tenant_id'], unique=False)

    # 2. Create webhook_deliveries table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('webhook_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('request_id', sa.Uuid(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_deliveries_webhook_id'), 'webhook_deliveries', ['webhook_id'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_tenant_id'), 'webhook_deliveries', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_request_id'), 'webhook_deliveries', ['request_id'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_status'), 'webhook_deliveries', ['status'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_next_attempt_at'), 'webhook_deliveries', ['next_attempt_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_webhook_deliveries_next_attempt_at'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_status'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_request_id'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_tenant_id'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_webhook_id'), table_name='webhook_deliveries')
    op.drop_table('webhook_deliveries')

    op.drop_index(op.f('ix_webhooks_tenant_id'), table_name='webhooks')
    op.drop_table('webhooks')
