from io import BytesIO
from uuid import uuid4
import hashlib

import pytest
from fastapi import UploadFile

from app.services.media_service import MediaService
from app.services.storage.local import LocalStorageService


class FailingStorage:
    def __init__(self):
        self.deleted = False

    def put(self, _object_key, _data):
        raise OSError("storage unavailable")

    def exists(self, _object_key):
        return True

    def delete(self, _object_key):
        self.deleted = True


def test_media_upload(tmp_path):
    storage = LocalStorageService(tmp_path)
    service = MediaService(storage=storage)

    content = b"fake image content"
    file = UploadFile(
        filename="photo.jpg",
        file=BytesIO(content),
    )

    tenant_id = uuid4()

    media = service.upload(file, tenant_id)

    assert media.storage_provider == "local"
    assert media.object_key.startswith(f"{tenant_id}/")
    assert media.object_key.endswith(".jpg")
    assert media.content_type == "application/octet-stream"
    assert media.size_bytes == len(content)
    assert media.checksum is not None

    with storage.open(media.object_key) as stored_file:
        assert stored_file.read() == content


def test_media_upload_checksum(tmp_path):
    storage = LocalStorageService(tmp_path)
    service = MediaService(storage=storage)

    content = b"hello moderashield"

    file = UploadFile(
        filename="audio.mp3",
        file=BytesIO(content),
    )

    media = service.upload(file, uuid4())

    expected_checksum = hashlib.sha256(content).hexdigest()

    assert media.checksum == expected_checksum
    assert media.size_bytes == len(content)


def test_media_upload_generates_unique_object_keys(tmp_path):
    storage = LocalStorageService(tmp_path)
    service = MediaService(storage=storage)

    tenant_id = uuid4()

    file1 = UploadFile(
        filename="video.mp4",
        file=BytesIO(b"video 1"),
    )

    file2 = UploadFile(
        filename="video.mp4",
        file=BytesIO(b"video 2"),
    )

    media1 = service.upload(file1, tenant_id)
    media2 = service.upload(file2, tenant_id)

    assert media1.object_key != media2.object_key


def test_media_storage_failure_attempts_cleanup():
    storage = FailingStorage()
    service = MediaService(storage=storage)
    file = UploadFile(filename="photo.jpg", file=BytesIO(b"content"))

    with pytest.raises(OSError, match="storage unavailable"):
        service.upload(file, uuid4())

    assert storage.deleted
