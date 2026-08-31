import ipaddress
import secrets
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.moderation import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.models.webhook import Webhook, WebhookDelivery


def generate_webhook_secret() -> str:
    return secrets.token_urlsafe(32)


def validate_webhook_url(url: str) -> str:
    """Reject non-HTTP URLs and literal non-public hosts to reduce SSRF risk."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Webhook URL must be an absolute HTTP(S) URL")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        # DNS is resolved by the HTTP client. Production deployments should
        # also enforce egress filtering to protect against DNS rebinding.
        return url
    if not address.is_global:
        raise HTTPException(status_code=422, detail="Webhook URL must target a public address")
    return url


def create_deliveries_for_request(db: Session, request: ModerationRequest, result: ModerationResult | None) -> None:
    """Create one durable, idempotent delivery per enabled tenant webhook."""
    webhooks = db.scalars(select(Webhook).where(Webhook.tenant_id == request.tenant_id, Webhook.enabled.is_(True))).all()
    if request.status == "failed":
        event_type, payload = "moderation.failed", {"event": "moderation.failed", "request_id": str(request.id), "status": "failed"}
    elif result is not None:
        event_type, payload = "moderation.completed", {
            "event": "moderation.completed", "request_id": str(request.id), "status": request.status,
            "is_flagged": result.is_flagged, "categories": result.category, "scores": result.score, "model": result.model,
        }
    else:
        return
    for webhook in webhooks:
        duplicate = db.scalar(select(WebhookDelivery.id).where(
            WebhookDelivery.webhook_id == webhook.id, WebhookDelivery.request_id == request.id,
            WebhookDelivery.event_type == event_type,
        ))
        if duplicate is None:
            db.add(WebhookDelivery(webhook_id=webhook.id, tenant_id=request.tenant_id, request_id=request.id,
                event_type=event_type, payload=payload, status="pending", next_attempt_at=datetime.now(timezone.utc)))
