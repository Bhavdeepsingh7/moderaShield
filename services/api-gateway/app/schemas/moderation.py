from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.media import MediaReference
from enum import Enum

class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class ModerationRequestCreate(BaseModel):
    content_type: ContentType
    content: str | None = None
    media: MediaReference | None = None

    @model_validator(mode="after")
    def validate_content(self):
        if self.content_type == ContentType.TEXT:
            if not self.content:
                raise ValueError("content is required for text moderation")

            if self.media is not None:
                raise ValueError("media is not allowed for text moderation")

        else:
            if self.media is None:
                raise ValueError(

                    f"media is required for {self.content_type.value} moderation "
                )

            if self.content is not None:
                raise ValueError(
                    f"content is not allowed for {self.content_type.value} moderation"

                )

        return self




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
