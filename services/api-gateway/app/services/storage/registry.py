from .base import StorageService
from .local import LocalStorageService
from .s3 import S3StorageService

from app.core.config import settings

def get_storage_service(storage_provider: str) -> StorageService:
    if storage_provider == "local":
        return LocalStorageService(settings.STORAGE_ROOT)
    if storage_provider == "s3":
        return S3StorageService(bucket=settings.S3_BUCKET, region=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL, access_key_id=settings.S3_ACCESS_KEY_ID,
            secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            connect_timeout=settings.S3_CONNECT_TIMEOUT_SECONDS,
            read_timeout=settings.S3_READ_TIMEOUT_SECONDS,
            server_side_encryption=settings.S3_SERVER_SIDE_ENCRYPTION)
    raise ValueError(f"Unsupported storage provider: {storage_provider}")
