from datetime import datetime
from uuid import UUID

from pydantic  import BaseModel, ConfigDict

class ApiKeyCreate(BaseModel):
    name: str

class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes = True)

    id: UUID
    name: str
    created_at: datetime
    is_active: bool

class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str