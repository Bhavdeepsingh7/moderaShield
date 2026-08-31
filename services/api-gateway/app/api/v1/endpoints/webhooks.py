from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.tenant import Tenant
from app.models.webhook import Webhook, WebhookDelivery
from app.schemas.webhook import WebhookCreate, WebhookCreatedResponse, WebhookResponse, WebhookUpdate, WebhookDeliveryResponse
from app.services.webhook_service import generate_webhook_secret, validate_webhook_url

router = APIRouter()


@router.post("/", response_model=WebhookCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(data: WebhookCreate, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    webhook = Webhook(tenant_id=tenant.id, url=validate_webhook_url(str(data.url)), secret=generate_webhook_secret())
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.get("/", response_model=list[WebhookResponse])
def list_webhooks(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    return db.scalars(select(Webhook).where(Webhook.tenant_id == tenant.id).order_by(Webhook.created_at.desc())).all()


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(webhook_id: UUID, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    webhook = db.scalar(select(Webhook).where(Webhook.id == webhook_id, Webhook.tenant_id == tenant.id))
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(webhook_id: UUID, data: WebhookUpdate, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    webhook = db.scalar(select(Webhook).where(Webhook.id == webhook_id, Webhook.tenant_id == tenant.id))
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    webhook.enabled = data.enabled
    db.commit()
    db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(webhook_id: UUID, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    webhook = db.scalar(select(Webhook).where(Webhook.id == webhook_id, Webhook.tenant_id == tenant.id))
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(webhook)
    db.commit()


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
def list_webhook_deliveries(webhook_id: UUID, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    # First make sure the webhook exists and belongs to this tenant to prevent cross-tenant enumeration
    webhook = db.scalar(select(Webhook).where(Webhook.id == webhook_id, Webhook.tenant_id == tenant.id))
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return db.scalars(select(WebhookDelivery).where(
        WebhookDelivery.webhook_id == webhook_id,
        WebhookDelivery.tenant_id == tenant.id
    ).order_by(WebhookDelivery.created_at.desc())).all()
