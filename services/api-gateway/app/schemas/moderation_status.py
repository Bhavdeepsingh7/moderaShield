from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

class ModerationStatusResponse(BaseModel):
    id: UUID
    status: str
    retry_count:  int
    last_error: str | None

    model_config = {
        "from_attributes": True,
    }