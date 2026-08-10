from sqlalchemy.orm import Session

from app.models.moderation import ModerationRequest
from app.models.tenant import Tenant
from app.repositories.moderation_repository import moderation_repository
from app.schemas.moderation import ModerationRequestCreate

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

        return moderation_repository.create(
            db,
            moderation_request,
        )


moderation_service = ModeratiionService()