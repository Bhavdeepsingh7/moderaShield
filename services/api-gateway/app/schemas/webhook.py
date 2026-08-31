from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl


class WebhookCreate(BaseModel):
    url: HttpUrl


class WebhookUpdate(BaseModel):
    enabled: bool


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    url: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class WebhookCreatedResponse(WebhookResponse):
    # Returned only by POST; never by GET/list.
    secret: str


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    webhook_id: UUID
    request_id: UUID
    event_type: str
    status: str
    attempt_count: int
    last_error: str | None
    next_attempt_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime
