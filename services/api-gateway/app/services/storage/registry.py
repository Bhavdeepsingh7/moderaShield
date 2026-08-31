from .base import StorageService
from .local import LocalStorageService

_STORAGE_SERVICES: dict[str, StorageService] = {
    "local": LocalStorageService("storage"),
}

def get_storage_service(storage_provider: str) -> StorageService:
    service = _STORAGE_SERVICES.get(storage_provider)

    if service is None:
        raise ValueError(
            f"Unsupported storage provider: {storage_provider}"
        )

    return service