from pydantic import BaseModel
from uuid import UUID

class TenantCreate(BaseModel):
    name: str
    slug: str

class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    status: str


model_config = {
    "from_attributes": True
}