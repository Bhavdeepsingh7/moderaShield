from hashlib import sha256
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.schemas.media import MediaReference
from app.services.storage.registry import get_storage_service

logger = logging.getLogger(__name__)

class MediaUploadTooLargeError(Exception):
    """Raised when a streamed upload exceeds the configured byte limit."""


class MediaService:

    def __init__(self, storage = None):
        self.storage = storage

    def upload(
        self,
        file: UploadFile,
        tenant_id,
        *,
        max_size_bytes: int | None = None,
        content_type: str | None = None,
    ) -> MediaReference:
        storage_provider = settings.STORAGE_PROVIDER
        storage = self.storage or  get_storage_service(storage_provider)

        extension = Path(file.filename or "").suffix.lower()

        object_key = (
            f"{tenant_id}/"
            f"{uuid4()}"
            f"{extension}"
        )

        hasher = sha256()
        size_bytes = 0

        class HashingStream:
            def __init__(self, source):
                self.source = source

            def read(self, size = -1):
                nonlocal size_bytes

                chunk = self.source.read(size)

                if chunk:
                    hasher.update(chunk)
                    size_bytes += len(chunk)
                    if max_size_bytes is not None and size_bytes > max_size_bytes:
                        raise MediaUploadTooLargeError(
                            f"Media upload exceeds the {max_size_bytes}-byte limit"
                        )

                return chunk

        stream = HashingStream(file.file)

        try:
            storage.put(object_key, stream)
        except Exception:
            # A limit/storage failure can occur after a partial local write.
            # Best-effort cleanup keeps this service safe when used directly.
            try:
                if storage.exists(object_key):
                    storage.delete(object_key)
            except Exception:
                # The caller still receives the original storage/upload error.
                logger.exception("Failed to clean up incomplete media upload")
            raise

        return MediaReference(
            storage_provider=storage_provider,
            object_key=object_key,
            content_type=content_type or file.content_type or "application/octet-stream",
            size_bytes=size_bytes,
            checksum=hasher.hexdigest(),
        )

    def delete(self, media: MediaReference) -> None:
        """Delete a previously returned reference using the configured registry."""
        storage = self.storage or get_storage_service(media.storage_provider)
        storage.delete(media.object_key)



media_service = MediaService()
