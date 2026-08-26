from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModerationRequestCreate(BaseModel):
    content_type: str
    content: str



class ModerationRequestResponse(BaseModel):
    """Fields available immediately after a moderation job is created."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    content_type: str
    status: str


class ModerationResultResponse(BaseModel):
    """Current moderation job state and its result when processing is complete."""

    id: UUID
    status: str
    is_flagged: bool | None = None
    categories: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    model: str | None = None
    created_at: datetime
    updated_at: datetime
