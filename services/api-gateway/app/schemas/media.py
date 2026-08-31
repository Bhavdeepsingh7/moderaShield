from pydantic import BaseModel , Field

class MediaReference(BaseModel):
    storage_provider: str
    object_key: str
    content_type: str
    size_bytes: int | None = Field(default=None,ge=0)
    checksum: str | None = None