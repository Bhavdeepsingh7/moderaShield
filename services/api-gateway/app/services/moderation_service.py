from sqlalchemy.orm import Session

from app.models.moderation import ModerationRequest
from app.models.tenant import Tenant
from app.repositories.moderation_repository import moderation_repository
from app.schemas.moderation import ModerationRequestCreate
from app.messaging.events import ModerationRequestEvent
from app.messaging.kafka import publish_moderation_request

class ModeratiionService:
    async def create_request(
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

        

        moderation_request =  moderation_repository.create(
            db,
            moderation_request,
        )

        event = ModerationRequestEvent(
            request_id=moderation_request.id,
            tenant_id = tenant.id,
            content_type=data.content_type,
        )

        await publish_moderation_request(event)

        return moderation_request


moderation_service = ModeratiionService()