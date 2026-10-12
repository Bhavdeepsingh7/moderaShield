"""Streaming S3-compatible implementation of the existing storage contract."""
from __future__ import annotations

import mimetypes
from typing import BinaryIO
from urllib.parse import urlparse

from .base import StorageService


class S3StorageService(StorageService):
    def __init__(self, *, bucket: str | None, region: str | None = None,
                 endpoint_url: str | None = None, access_key_id: str | None = None,
                 secret_access_key: str | None = None, connect_timeout: int = 5,
                 read_timeout: int = 60, server_side_encryption: str | None = None,
                 client=None):
        if not bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_PROVIDER=s3")
        if endpoint_url:
            parsed = urlparse(endpoint_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("S3_ENDPOINT_URL must be an absolute HTTP(S) URL")
        self.bucket, self.server_side_encryption = bucket, server_side_encryption
        if client is not None:
            self.client = client
            return
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # clear deployment error without exposing credentials
            raise RuntimeError("boto3 is required for STORAGE_PROVIDER=s3") from exc
        self.client = boto3.client(
            "s3", region_name=region, endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key,
            config=Config(connect_timeout=connect_timeout, read_timeout=read_timeout, retries={"max_attempts": 3, "mode": "standard"}),
        )

    @staticmethod
    def _is_missing(error: Exception) -> bool:
        code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
        return str(code) in {"404", "NoSuchKey", "NotFound"}

    def put(self, object_key: str, data: BinaryIO) -> None:
        args = {"Bucket": self.bucket, "Key": object_key, "Body": data,
                "ContentType": mimetypes.guess_type(object_key)[0] or "application/octet-stream"}
        if self.server_side_encryption:
            args["ServerSideEncryption"] = self.server_side_encryption
        self.client.put_object(**args)

    def open(self, object_key: str) -> BinaryIO:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=object_key)["Body"]
        except Exception as exc:
            if self._is_missing(exc):
                raise FileNotFoundError(object_key) from exc
            raise

    def delete(self, object_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=object_key)

    def exists(self, object_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except Exception as exc:
            if self._is_missing(exc):
                return False
            raise
