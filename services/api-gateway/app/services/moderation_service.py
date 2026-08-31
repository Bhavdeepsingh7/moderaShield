from sqlalchemy.orm import Session

import json
from app.models.moderation import ModerationRequest
from app.models.tenant import Tenant
from app.models.outbox import OutboxEvent
from app.repositories.moderation_repository import moderation_repository
from app.schemas.moderation import ModerationRequestCreate
from app.messaging.events import ModerationRequestEvent
from app.messaging.kafka import publish_moderation_request
from app.models.moderation_asset import ModerationAsset

class ModeratiionService:
    def create_request(
            self,
            db:Session,
            tenant: Tenant,
            data:ModerationRequestCreate
    ) -> ModerationRequest:
        moderation_request = ModerationRequest(
            tenant_id = tenant.id,
            content_type= data.content_type,
            content = data.content,
            status="pending",
        )

        db.add(moderation_request)

        db.flush()

        asset = None

        if data.media is not None:
            asset = ModerationAsset(
                request_id = moderation_request.id,
                storage_provider = data.media.storage_provider,
                object_key = data.media.object_key,
                mime_type = data.media.mime_type,
                size_bytes = data.media.size_bytes,
                checksum = data.media.checksum,
            )

            db.add(asset)
            db.flush()

        event_payload= {
            "request_id": str(moderation_request.id),
            "tenant_id": str(tenant.id),
            "content_type": data.content_type.value,
        }

        if asset is not None:
            event_payload["asset_id"] = str(asset.id)

        outbox_event = OutboxEvent(
            event_type = "moderation.requested",
            aggregate_id = moderation_request.id,
            payload = json.dumps(event_payload),
            status="pending",
        )

        db.add(outbox_event)

        db.commit()
        db.refresh(moderation_request)

        return moderation_request


moderation_service = ModeratiionService()