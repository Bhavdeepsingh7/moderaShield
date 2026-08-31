import pytest

from app.services.storage.local import LocalStorageService
from app.services.storage.registry import get_storage_service


def test_local_storage_provider():
    service = get_storage_service("local")

    assert isinstance(service, LocalStorageService)


def test_unknown_storage_provider():
    with pytest.raises(ValueError, match="Unsupported storage provider"):
        get_storage_service("s3")