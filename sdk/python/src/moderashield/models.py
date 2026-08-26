"""Typed API response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModerationSubmission(BaseModel):
    """The asynchronous job returned by POST /moderate/."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    tenant_id: UUID
    content_type: str
    status: str


class ModerationResult(BaseModel):
    """The current or terminal state of a text moderation job."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    status: str
    is_flagged: bool | None = None
    categories: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    model: str | None = None
    created_at: datetime
    updated_at: datetime
