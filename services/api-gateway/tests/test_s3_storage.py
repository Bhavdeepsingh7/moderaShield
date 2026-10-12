from io import BytesIO

import pytest

from app.services.storage.s3 import S3StorageService


class NotFound(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class FakeS3:
    def __init__(self): self.objects, self.put_calls = {}, []
    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        self.objects[kwargs["Key"]] = kwargs["Body"].read()
    def get_object(self, **kwargs):
        if kwargs["Key"] not in self.objects: raise NotFound()
        return {"Body": BytesIO(self.objects[kwargs["Key"]])}
    def head_object(self, **kwargs):
        if kwargs["Key"] not in self.objects: raise NotFound()
    def delete_object(self, **kwargs): self.objects.pop(kwargs["Key"], None)


def test_s3_storage_streaming_crud_content_type_and_missing_object():
    client = FakeS3()
    storage = S3StorageService(bucket="test-private", client=client, server_side_encryption="AES256")
    key = "tenant-1/media/photo.jpg"
    storage.put(key, BytesIO(b"image-bytes"))
    assert storage.exists(key)
    assert client.put_calls[0]["ContentType"] == "image/jpeg"
    assert client.put_calls[0]["ServerSideEncryption"] == "AES256"
    with storage.open(key) as body: assert body.read() == b"image-bytes"
    storage.delete(key)
    assert not storage.exists(key)
    with pytest.raises(FileNotFoundError): storage.open(key)


def test_s3_configuration_fails_without_bucket_or_with_bad_endpoint():
    with pytest.raises(ValueError, match="S3_BUCKET"):
        S3StorageService(bucket=None, client=FakeS3())
    with pytest.raises(ValueError, match="HTTP"):
        S3StorageService(bucket="bucket", endpoint_url="file:///tmp", client=FakeS3())
