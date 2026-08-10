from uuid import UUID

from pydantic import BaseModel , ConfigDict

class ModerationRequestCreate(BaseModel):
    content_type: str
    content: str

class ModerationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes = True)

    id: UUID
    tenant_id: UUID
    content_type: str
    status: str
    