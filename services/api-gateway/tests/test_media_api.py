import json
import os
from io import BytesIO
from uuid import UUID, uuid4

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
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
from app.services.storage.local import LocalStorageService


@pytest.fixture
def media_client(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tenant = Tenant(name="media-owner", slug="media-owner", status="active")
    with factory.begin() as db:
        db.add(tenant)

    storage = LocalStorageService(tmp_path)
    monkeypatch.setattr(moderation_endpoint.media_service, "storage", storage)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/moderate")

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_tenant] = lambda: tenant
    with TestClient(app) as client:
        yield client, factory, tenant, storage
    Base.metadata.drop_all(engine)


@pytest.mark.parametrize(
    ("mime_type", "expected_content_type"),
    [
        ("image/jpeg", "image"),
        ("audio/mpeg", "audio"),
        ("video/mp4", "video"),
    ],
)
def test_media_upload_creates_asset_request_outbox_and_storage(
    media_client, mime_type, expected_content_type
):
    client, factory, tenant, storage = media_client
    content = b"media payload"

    response = client.post(
        "/api/v1/moderate/media",
        files={"file": ("upload.bin", content, mime_type)},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == expected_content_type
    assert body["status"] == "pending"
    assert body["tenant_id"] == str(tenant.id)
    with factory() as db:
        request = db.get(ModerationRequest, UUID(body["id"]))
        asset = db.get(ModerationAsset, request.asset_id)
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == request.id))
        payload = json.loads(event.payload)

        assert request.asset_id == asset.id
        assert asset.tenant_id == tenant.id
        assert asset.storage_provider == "local"
        assert asset.object_key
        assert asset.mime_type == mime_type
        assert asset.size_bytes == len(content)
        assert asset.checksum
        assert storage.exists(asset.object_key)
        assert payload == {
            "request_id": str(request.id),
            "tenant_id": str(tenant.id),
            "content_type": expected_content_type,
            "asset_id": str(asset.id),
        }
        assert content.decode() not in event.payload
        assert event.event_type == "moderation.requested"


@pytest.mark.parametrize("mime_type", ["text/plain", "application/pdf"])
def test_unsupported_media_is_rejected_without_side_effects(media_client, mime_type):
    client, factory, _, storage = media_client
    response = client.post(
        "/api/v1/moderate/media",
        files={"file": ("unsupported", b"nope", mime_type)},
    )
    assert response.status_code == 415
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ModerationRequest)) == 0
        assert db.scalar(select(func.count()).select_from(ModerationAsset)) == 0
    assert list(storage.root.rglob("*")) == []


def test_missing_media_content_type_is_rejected(media_client):
    client, factory, _, _ = media_client
    response = client.post(
        "/api/v1/moderate/media",
        files={"file": ("missing", b"payload", None)},
    )
    assert response.status_code == 415
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ModerationRequest)) == 0


def test_oversized_media_is_rejected_and_cleaned_up(media_client, monkeypatch):
    client, factory, _, storage = media_client
    monkeypatch.setattr(moderation_endpoint.settings, "MAX_MEDIA_SIZE_BYTES", 3)
    response = client.post(
        "/api/v1/moderate/media",
        files={"file": ("large.jpg", b"four", "image/jpeg")},
    )
    assert response.status_code == 413
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ModerationRequest)) == 0
        assert db.scalar(select(func.count()).select_from(ModerationAsset)) == 0
    assert list(storage.root.rglob("*")) == []


def test_db_failure_removes_uploaded_object(media_client, monkeypatch):
    client, factory, _, storage = media_client

    def fail_create(*_args, **_kwargs):
        raise RuntimeError("database write failed")

    monkeypatch.setattr(moderation_endpoint.moderation_service, "create_request", fail_create)
    # The application error is deliberately preserved after cleanup.
    with pytest.raises(RuntimeError, match="database write failed"):
        client.post(
            "/api/v1/moderate/media",
            files={"file": ("image.jpg", b"payload", "image/jpeg")},
        )
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ModerationRequest)) == 0
    assert list(storage.root.rglob("*")) == []


def test_media_reference_cannot_be_supplied_to_json_endpoint(media_client):
    client, _, _, _ = media_client
    response = client.post(
        "/api/v1/moderate/",
        json={
            "content_type": "image",
            "media": {
                "storage_provider": "local",
                "object_key": "another-tenant/private.jpg",
                "content_type": "image/jpeg",
            },
        },
    )
    assert response.status_code == 400


def test_other_tenant_cannot_retrieve_media_request(media_client):
    client, factory, _, _ = media_client
    response = client.post(
        "/api/v1/moderate/media",
        files={"file": ("image.jpg", b"payload", "image/jpeg")},
    )
    request_id = response.json()["id"]
    other = Tenant(name="other-media-owner", slug="other-media-owner", status="active")
    with factory.begin() as db:
        db.add(other)

    client.app.dependency_overrides[get_current_tenant] = lambda: other
    assert client.get(f"/api/v1/moderate/{request_id}").status_code == 404
