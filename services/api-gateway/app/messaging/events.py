from uuid import UUID
from pydantic import BaseModel

class ModerationRequestEvent(BaseModel):
    request_id: UUID
    tenant_id: UUID
    content_type: str
    