from io import BytesIO

import pytest

from app.services.storage.local import LocalStorageService


def test_put_and_open(tmp_path):
    storage = LocalStorageService(tmp_path)

    data = BytesIO(b"hello moderashield")

    storage.put("tenant-1/test.txt", data)

    assert storage.exists("tenant-1/test.txt")

    with storage.open("tenant-1/test.txt") as stored:
        assert stored.read() == b"hello moderashield"


def test_delete(tmp_path):
    storage = LocalStorageService(tmp_path)

    storage.put("tenant-1/test.txt", BytesIO(b"hello"))

    assert storage.exists("tenant-1/test.txt")

    storage.delete("tenant-1/test.txt")

    assert not storage.exists("tenant-1/test.txt")


def test_missing_object(tmp_path):
    storage = LocalStorageService(tmp_path)

    assert not storage.exists("does-not-exist.txt")

    with pytest.raises(FileNotFoundError):
        storage.open("does-not-exist.txt")


def test_path_traversal_is_rejected(tmp_path):
    storage = LocalStorageService(tmp_path)

    with pytest.raises(ValueError):
        storage.put("../../outside.txt", BytesIO(b"bad"))