import io
import os
import concurrent.futures
from uuid import UUID, uuid4

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import moderation as moderation_endpoint
from app.api.v1.endpoints.moderation import router
from app.db.base import Base
import app.db.models  # noqa: F401 - registers mapped tables
from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.moderation import ModerationRequest
from app.models.moderation_asset import ModerationAsset
from app.models.outbox import OutboxEvent
from app.models.tenant import Tenant
from app.schemas.media import MediaReference
from app.schemas.moderation import ContentType, ModerationRequestCreate
from app.services.idempotency import compute_request_hash
from app.services.storage.local import LocalStorageService


@pytest.fixture
def media_app_env(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    storage = LocalStorageService(storage_dir)
    monkeypatch.setattr(moderation_endpoint.media_service, "storage", storage)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug=f"tenant-a-{uuid4()}", status="active")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug=f"tenant-b-{uuid4()}", status="active")

    with factory.begin() as db:
        db.add(tenant_a)
        db.add(tenant_b)

    current_tenant_holder = {"tenant": tenant_a}

    def override_tenant():
        return current_tenant_holder["tenant"]

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/moderate")
    app.dependency_overrides[get_current_tenant] = override_tenant
    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as client:
        yield client, factory, tenant_a, tenant_b, current_tenant_holder, storage_dir

    Base.metadata.drop_all(engine)


def count_files_in_dir(path):
    count = 0
    for root, _, files in os.walk(path):
        count += len(files)
    return count


def test_media_hash_determinism():
    media1 = MediaReference(
        storage_provider="local",
        object_key="key1",
        content_type="image/jpeg",
        size_bytes=100,
        checksum="hash1234",
    )
    media2 = MediaReference(
        storage_provider="local",
        object_key="key2",
        content_type="image/jpeg",
        size_bytes=100,
        checksum="hash1234",
    )
    media3 = MediaReference(
        storage_provider="local",
        object_key="key3",
        content_type="image/jpeg",
        size_bytes=100,
        checksum="hash5678",
    )

    data1 = ModerationRequestCreate(content_type=ContentType.IMAGE, media=media1)
    data2 = ModerationRequestCreate(content_type=ContentType.IMAGE, media=media2)
    data3 = ModerationRequestCreate(content_type=ContentType.IMAGE, media=media3)

    hash1 = compute_request_hash(data1)
    hash2 = compute_request_hash(data2)
    hash3 = compute_request_hash(data3)

    assert len(hash1) == 64
    assert hash1 == hash2
    assert hash1 != hash3


def test_media_no_idempotency_key(media_app_env):
    client, factory, tenant_a, _, _, storage_dir = media_app_env

    file_bytes = b"sample image content 1"
    files = {"file": ("test.jpg", io.BytesIO(file_bytes), "image/jpeg")}

    response = client.post("/api/v1/moderate/media", files=files)
    assert response.status_code == 201
    res_data = response.json()
    req_uuid = UUID(res_data["id"])

    with factory() as db:
        req = db.scalar(select(ModerationRequest).where(ModerationRequest.id == req_uuid))
        assert req is not None
        assert req.idempotency_key is None
        assert req.request_hash is None

        asset_count = db.scalar(select(func.count(ModerationAsset.id)).where(ModerationAsset.tenant_id == tenant_a.id))
        assert asset_count == 1

        outbox_count = db.scalar(select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == req_uuid))
        assert outbox_count == 1

    assert count_files_in_dir(storage_dir) == 1


def test_first_media_request_with_key(media_app_env):
    client, factory, tenant_a, _, _, storage_dir = media_app_env
    key = "media-key-001"

    file_bytes = b"sample image content 2"
    files = {"file": ("image.jpg", io.BytesIO(file_bytes), "image/jpeg")}

    response = client.post(
        "/api/v1/moderate/media",
        headers={"Idempotency-Key": key},
        files=files,
    )
    assert response.status_code == 201
    res_data = response.json()
    req_uuid = UUID(res_data["id"])

    with factory() as db:
        req = db.scalar(select(ModerationRequest).where(ModerationRequest.id == req_uuid))
        assert req is not None
        assert req.idempotency_key == key
        assert req.request_hash is not None
        assert len(req.request_hash) == 64

        asset_count = db.scalar(select(func.count(ModerationAsset.id)).where(ModerationAsset.tenant_id == tenant_a.id))
        assert asset_count == 1

        outbox_count = db.scalar(select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == req_uuid))
        assert outbox_count == 1

    assert count_files_in_dir(storage_dir) == 1


def test_retry_same_key_identical_media(media_app_env):
    client, factory, tenant_a, _, _, storage_dir = media_app_env
    key = "media-retry-key"
    file_bytes = b"same image content"

    files1 = {"file": ("image.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    resp1 = client.post("/api/v1/moderate/media", headers={"Idempotency-Key": key}, files=files1)
    assert resp1.status_code == 201

    files2 = {"file": ("image.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    resp2 = client.post("/api/v1/moderate/media", headers={"Idempotency-Key": key}, files=files2)
    assert resp2.status_code == 201

    assert resp1.json()["id"] == resp2.json()["id"]
    req_uuid = UUID(resp1.json()["id"])

    with factory() as db:
        req_count = db.scalar(select(func.count(ModerationRequest.id)).where(ModerationRequest.tenant_id == tenant_a.id))
        assert req_count == 1

        asset_count = db.scalar(select(func.count(ModerationAsset.id)).where(ModerationAsset.tenant_id == tenant_a.id))
        assert asset_count == 1

        outbox_count = db.scalar(select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == req_uuid))
        assert outbox_count == 1

    # Duplicate uploaded object MUST be cleaned up; exactly 1 file remains in storage
    assert count_files_in_dir(storage_dir) == 1


def test_same_key_different_media_conflict(media_app_env):
    client, factory, tenant_a, _, _, storage_dir = media_app_env
    key = "media-conflict-key"

    files1 = {"file": ("image1.jpg", io.BytesIO(b"image A"), "image/jpeg")}
    resp1 = client.post("/api/v1/moderate/media", headers={"Idempotency-Key": key}, files=files1)
    assert resp1.status_code == 201
    req_uuid = UUID(resp1.json()["id"])

    files2 = {"file": ("image2.jpg", io.BytesIO(b"image B different"), "image/jpeg")}
    resp2 = client.post("/api/v1/moderate/media", headers={"Idempotency-Key": key}, files=files2)
    assert resp2.status_code == 409
    assert "already used with a different request payload" in resp2.json()["detail"]

    with factory() as db:
        req_count = db.scalar(select(func.count(ModerationRequest.id)).where(ModerationRequest.tenant_id == tenant_a.id))
        assert req_count == 1

        asset_count = db.scalar(select(func.count(ModerationAsset.id)).where(ModerationAsset.tenant_id == tenant_a.id))
        assert asset_count == 1

        outbox_count = db.scalar(select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == req_uuid))
        assert outbox_count == 1

    # Rejected duplicate file MUST be cleaned up; exactly 1 file remains in storage
    assert count_files_in_dir(storage_dir) == 1


def test_media_same_key_across_different_tenants(media_app_env):
    client, factory, tenant_a, tenant_b, current_tenant_holder, storage_dir = media_app_env
    key = "media-tenant-shared-key"
    file_bytes = b"shared tenant media"

    current_tenant_holder["tenant"] = tenant_a
    files_a = {"file": ("img.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    resp_a = client.post("/api/v1/moderate/media", headers={"Idempotency-Key": key}, files=files_a)
    assert resp_a.status_code == 201

    current_tenant_holder["tenant"] = tenant_b
    files_b = {"file": ("img.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    resp_b = client.post("/api/v1/moderate/media", headers={"Idempotency-Key": key}, files=files_b)
    assert resp_b.status_code == 201

    assert resp_a.json()["id"] != resp_b.json()["id"]

    with factory() as db:
        req_count = db.scalar(select(func.count(ModerationRequest.id)).where(ModerationRequest.idempotency_key == key))
        assert req_count == 2

        asset_count = db.scalar(select(func.count(ModerationAsset.id)))
        assert asset_count == 2

    assert count_files_in_dir(storage_dir) == 2


def test_media_key_length_validation(media_app_env):
    client, _, _, _, _, _ = media_app_env
    long_key = "m" * 256
    files = {"file": ("image.jpg", io.BytesIO(b"valid content"), "image/jpeg")}

    response = client.post(
        "/api/v1/moderate/media",
        headers={"Idempotency-Key": long_key},
        files=files,
    )
    assert response.status_code == 422


def test_concurrent_identical_media_requests(media_app_env):
    client, factory, tenant_a, _, _, storage_dir = media_app_env
    key = "conc-media-same"
    file_bytes = b"concurrent image bytes"

    def make_call():
        files = {"file": ("image.jpg", io.BytesIO(file_bytes), "image/jpeg")}
        return client.post("/api/v1/moderate/media", headers={"Idempotency-Key": key}, files=files)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_call) for _ in range(5)]
        results = [f.result() for f in futures]

    status_codes = [r.status_code for r in results]
    assert all(code == 201 for code in status_codes)

    request_ids = {r.json()["id"] for r in results}
    assert len(request_ids) == 1
    winning_uuid = UUID(list(request_ids)[0])

    with factory() as db:
        req_count = db.scalar(select(func.count(ModerationRequest.id)).where(ModerationRequest.tenant_id == tenant_a.id))
        assert req_count == 1

        asset_count = db.scalar(select(func.count(ModerationAsset.id)).where(ModerationAsset.tenant_id == tenant_a.id))
        assert asset_count == 1

        outbox_count = db.scalar(select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == winning_uuid))
        assert outbox_count == 1

    # Exactly 1 object in storage (all 4 losing duplicate uploads cleaned up)
    assert count_files_in_dir(storage_dir) == 1


def test_concurrent_different_media_requests(media_app_env):
    client, factory, tenant_a, _, _, storage_dir = media_app_env
    key = "conc-media-diff"

    def make_call(i):
        file_bytes = f"unique media payload {i}".encode()
        files = {"file": (f"img_{i}.jpg", io.BytesIO(file_bytes), "image/jpeg")}
        return client.post("/api/v1/moderate/media", headers={"Idempotency-Key": key}, files=files)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_call, i) for i in range(5)]
        results = [f.result() for f in futures]

    successes = [r for r in results if r.status_code == 201]
    conflicts = [r for r in results if r.status_code == 409]

    assert len(successes) == 1
    assert len(conflicts) == 4

    winning_uuid = UUID(successes[0].json()["id"])

    with factory() as db:
        req_count = db.scalar(select(func.count(ModerationRequest.id)).where(ModerationRequest.tenant_id == tenant_a.id))
        assert req_count == 1

        asset_count = db.scalar(select(func.count(ModerationAsset.id)).where(ModerationAsset.tenant_id == tenant_a.id))
        assert asset_count == 1

        outbox_count = db.scalar(select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == winning_uuid))
        assert outbox_count == 1

    # Exactly 1 object in storage (all 4 losing duplicate uploads cleaned up)
    assert count_files_in_dir(storage_dir) == 1


def test_media_validation_retained(media_app_env, monkeypatch):
    client, _, _, _, _, _ = media_app_env

    # Unsupported MIME type
    invalid_files = {"file": ("doc.txt", io.BytesIO(b"text content"), "text/plain")}
    resp = client.post("/api/v1/moderate/media", files=invalid_files)
    assert resp.status_code == 415

    # Oversized media rejection
    monkeypatch.setattr(moderation_endpoint.settings, "MAX_MEDIA_SIZE_BYTES", 3)
    oversized_files = {"file": ("large.jpg", io.BytesIO(b"four"), "image/jpeg")}
    resp_oversized = client.post("/api/v1/moderate/media", files=oversized_files)
    assert resp_oversized.status_code == 413
