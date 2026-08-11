from sqlalchemy.orm import Session

import json
from app.models.moderation import ModerationRequest
from app.models.tenant import Tenant
from app.models.outbox import OutboxEvent
from app.repositories.moderation_repository import moderation_repository
from app.schemas.moderation import ModerationRequestCreate
from app.messaging.events import ModerationRequestEvent
from app.messaging.kafka import publish_moderation_request

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

        event_payload= {
            "request_id": str(moderation_request.id),
            "tenant_id": str(tenant.id),
            "content_type": data.content_type,
        }

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