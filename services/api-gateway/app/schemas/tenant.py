from pydantic import BaseModel

class TenantCreate(BaseModel):
    name: str
    slug: str

class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    status: str


model_config = {
    "from_attributes": True
}