from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

import json
import logging
import uuid
from app.models.moderation import ModerationRequest
from app.models.tenant import Tenant
from app.models.outbox import OutboxEvent
from app.repositories.moderation_repository import moderation_repository
from app.schemas.moderation import ModerationRequestCreate
from app.messaging.events import ModerationRequestEvent
from app.messaging.kafka import publish_moderation_request
from app.models.moderation_asset import ModerationAsset
from app.services.idempotency import compute_request_hash
from app.services.media_service import media_service

logger = logging.getLogger(__name__)


class ModeratiionService:
    def create_request(
        self,
        db: Session,
        tenant: Tenant,
        data: ModerationRequestCreate,
        idempotency_key: str | None = None,
    ) -> ModerationRequest:
        request_hash: str | None = None

        if idempotency_key is not None:
            if len(idempotency_key) > 255:
                if data.media is not None:
                    try:
                        media_service.delete(data.media)
                    except Exception:
                        logger.exception("Failed to clean up media after key validation failure")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Idempotency-Key header cannot exceed 255 characters",
                )

            request_hash = compute_request_hash(data)

            existing_request = db.scalar(
                select(ModerationRequest).where(
                    ModerationRequest.tenant_id == tenant.id,
                    ModerationRequest.idempotency_key == idempotency_key,
                )
            )

            if existing_request is not None:
                if data.media is not None:
                    try:
                        media_service.delete(data.media)
                    except Exception:
                        logger.exception("Failed to clean up media after duplicate key lookup")

                if existing_request.request_hash == request_hash:
                    return existing_request
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Idempotency key '{idempotency_key}' was already used with a different request payload.",
                    )

        asset = None

        if data.media is not None:
            asset = ModerationAsset(
                tenant_id=tenant.id,
                storage_provider=data.media.storage_provider,
                object_key=data.media.object_key,
                mime_type=data.media.content_type,
                size_bytes=data.media.size_bytes,
                checksum=data.media.checksum,
                asset_metadata=data.media.asset_metadata,
            )

            db.add(asset)
            db.flush()

        moderation_request = ModerationRequest(
            tenant_id=tenant.id,
            content_type=data.content_type.value,
            content=data.content,
            asset_id=asset.id if asset else None,
            status="pending",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )

        if idempotency_key is not None:
            try:
                with db.begin_nested():
                    db.add(moderation_request)
                    db.flush()
            except IntegrityError:
                if data.media is not None:
                    try:
                        media_service.delete(data.media)
                    except Exception:
                        logger.exception("Failed to clean up media after race condition")

                existing_request = db.scalar(
                    select(ModerationRequest).where(
                        ModerationRequest.tenant_id == tenant.id,
                        ModerationRequest.idempotency_key == idempotency_key,
                    )
                )
                if existing_request is not None:
                    if existing_request.request_hash == request_hash:
                        return existing_request
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Idempotency key '{idempotency_key}' was already used with a different request payload.",
                        )
                raise
        else:
            db.add(moderation_request)
            db.flush()

        outbox_id = uuid.uuid4()
        event_payload = {
            "event_id": str(outbox_id),
            "request_id": str(moderation_request.id),
            "tenant_id": str(tenant.id),
            "content_type": data.content_type.value,
        }

        if asset is not None:
            event_payload["asset_id"] = str(asset.id)

        outbox_event = OutboxEvent(
            id=outbox_id,
            event_type="moderation.requested",
            aggregate_id=moderation_request.id,
            payload=json.dumps(event_payload),
            status="pending",
        )

        db.add(outbox_event)

        db.commit()
        db.refresh(moderation_request)

        return moderation_request


moderation_service = ModeratiionService()
