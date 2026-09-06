from .base import StorageService
from .local import LocalStorageService

from app.core.config import settings

_STORAGE_SERVICES: dict[str, StorageService] = {
    "local": LocalStorageService(settings.STORAGE_ROOT),
}

def get_storage_service(storage_provider: str) -> StorageService:
    service = _STORAGE_SERVICES.get(storage_provider)

    if service is None:
        raise ValueError(
            f"Unsupported storage provider: {storage_provider}"
        )

    return service