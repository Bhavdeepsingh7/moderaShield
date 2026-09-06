import asyncio
import io
import json
import os
from uuid import UUID, uuid4

from PIL import Image
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import moderation as moderation_endpoint
from app.api.v1.endpoints.moderation import router
from app.db.base import Base
import app.db.models  # registers mapped tables
from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.moderation import ModerationRequest
from app.models.moderation_asset import ModerationAsset
from app.models.moderation_result import ModerationResult
from app.models.outbox import OutboxEvent
from app.models.tenant import Tenant
from app.models.webhook import Webhook, WebhookDelivery
from app.services.inference.image_handler import ImageModerationHandler
from app.services.inference.registry import get_moderation_handler
from app.services.media.exceptions import ImageCorruptError
from app.services.storage.local import LocalStorageService
from app.workers import moderation_worker


def _make_test_image_bytes(format="PNG", size=(64, 64), color="blue"):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


class Message:
    def __init__(self, request_id):
        self.value = json.dumps({"request_id": str(request_id)}).encode()


@pytest.fixture
def image_pipeline_env(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(moderation_worker, "SessionLocal", factory)

    storage = LocalStorageService(tmp_path / "storage")
    monkeypatch.setattr(moderation_endpoint.media_service, "storage", storage)

    monkeypatch.setattr(
        "app.services.media.asset_resolver.get_storage_service",
        lambda provider: storage,
    )

    yield factory, storage

    Base.metadata.drop_all(engine)


def test_image_moderation_end_to_end_flow(image_pipeline_env, monkeypatch):
    factory, storage = image_pipeline_env

    tenant = Tenant(id=uuid4(), name="e2e-tenant", slug="e2e-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)
        webhook = Webhook(
            id=uuid4(),
            tenant_id=tenant.id,
            url="https://example.com/webhook",
            secret="test-secret",
            enabled=True,
        )
        db.add(webhook)

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

    # 1. API image upload
    image_bytes = _make_test_image_bytes(format="PNG", size=(50, 50))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/moderate/media",
            files={"file": ("photo.png", image_bytes, "image/png")},
        )
        assert response.status_code == 201
        res_data = response.json()
        request_id = UUID(res_data["id"])
        assert res_data["content_type"] == "image"
        assert res_data["status"] == "pending"

    # Verify initial DB state, asset, outbox, and storage
    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req is not None
        assert req.asset_id is not None
        assert req.content is None  # Never store image bytes in content!
        asset = db.get(ModerationAsset, req.asset_id)
        assert asset is not None
        assert asset.mime_type == "image/png"
        assert storage.exists(asset.object_key)

        outbox = db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == request_id))
        assert outbox is not None
        outbox_payload = json.loads(outbox.payload)
        assert outbox_payload["request_id"] == str(request_id)
        assert outbox_payload["asset_id"] == str(asset.id)
        assert "photo.png" not in outbox.payload
        assert len(outbox.payload) < 500  # No raw bytes leaked!

    # 2. Worker consumes message
    class MockInference:
        calls = 0

        def moderate(self, image):
            self.calls += 1
            assert isinstance(image, Image.Image)
            return {
                "is_flagged": False,
                "categories": [],
                "scores": {"normal": 0.98, "nsfw": 0.02},
                "model": "test-vit-model",
            }

    mock_inf = MockInference()
    handler = ImageModerationHandler(inference_service=mock_inf)
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    asyncio.run(moderation_worker.process_message(Message(request_id)))

    # 3. Verify final DB state and webhook delivery
    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req.status == "approved"
        assert req.retry_count == 0

        mod_res = db.scalar(select(ModerationResult).where(ModerationResult.request_id == request_id))
        assert mod_res is not None
        assert mod_res.is_flagged is False
        assert mod_res.category == []
        assert mod_res.score == {"normal": 0.98, "nsfw": 0.02}
        assert mod_res.model == "test-vit-model"

        # Check webhook delivery created
        delivery = db.scalar(select(WebhookDelivery).where(WebhookDelivery.request_id == request_id))
        assert delivery is not None
        assert delivery.event_type == "moderation.completed"
        assert delivery.payload["status"] == "approved"
        assert delivery.payload["is_flagged"] is False
        assert delivery.payload["model"] == "test-vit-model"
        assert "data" not in delivery.payload
        assert "bytes" not in delivery.payload

    # 4. Duplicate message idempotency: duplicate delivery does not re-run inference
    asyncio.run(moderation_worker.process_message(Message(request_id)))
    assert mock_inf.calls == 1

    # 5. Verify status retrieval endpoint
    with TestClient(app) as client:
        status_resp = client.get(f"/api/v1/moderate/{request_id}")
        assert status_resp.status_code == 200
        body = status_resp.json()
        assert body["status"] == "approved"
        assert body["is_flagged"] is False
        assert body["scores"] == {"normal": 0.98, "nsfw": 0.02}
        assert body["model"] == "test-vit-model"


def test_image_flagged_moderation(image_pipeline_env, monkeypatch):
    factory, storage = image_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="flag-tenant", slug="flag-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)

    # Put a valid image in storage
    image_bytes = _make_test_image_bytes(color="red")
    object_key = f"{tenant_id}/{uuid4()}.png"
    storage.put(object_key, io.BytesIO(image_bytes))

    with factory.begin() as db:
        asset = ModerationAsset(
            id=uuid4(),
            tenant_id=tenant_id,
            storage_provider="local",
            object_key=object_key,
            mime_type="image/png",
            size_bytes=len(image_bytes),
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            id=uuid4(),
            tenant_id=tenant_id,
            content_type="image",
            content=None,
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)

    class MockFlaggedInference:
        def moderate(self, image):
            return {
                "is_flagged": True,
                "categories": ["nsfw"],
                "scores": {"normal": 0.05, "nsfw": 0.95},
                "model": "test-vit-model",
            }

    handler = ImageModerationHandler(inference_service=MockFlaggedInference())
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    asyncio.run(moderation_worker.process_message(Message(req.id)))

    with factory() as db:
        stored = db.get(ModerationRequest, req.id)
        assert stored.status == "flagged"
        result = db.scalar(select(ModerationResult).where(ModerationResult.request_id == req.id))
        assert result.is_flagged is True
        assert result.category == ["nsfw"]


def test_corrupted_image_causes_terminal_failure(image_pipeline_env, monkeypatch):
    factory, storage = image_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="fail-tenant", slug="fail-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)
        webhook = Webhook(
            id=uuid4(),
            tenant_id=tenant_id,
            url="https://example.com/webhook",
            secret="test-secret",
            enabled=True,
        )
        db.add(webhook)

    # Store corrupted/non-image bytes
    object_key = f"{tenant_id}/{uuid4()}.png"
    storage.put(object_key, io.BytesIO(b"This is not a real image at all!"))

    with factory.begin() as db:
        asset = ModerationAsset(
            id=uuid4(),
            tenant_id=tenant_id,
            storage_provider="local",
            object_key=object_key,
            mime_type="image/png",
            size_bytes=32,
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            id=uuid4(),
            tenant_id=tenant_id,
            content_type="image",
            content=None,
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)

    handler = ImageModerationHandler()
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    # Must fail terminally without raising RetriableProcessingError
    asyncio.run(moderation_worker.process_message(Message(req.id)))

    with factory() as db:
        stored = db.get(ModerationRequest, req.id)
        assert stored.status == "failed"
        assert stored.retry_count == 1
        assert "Cannot identify or decode image" in stored.last_error
        # ModerationResult is not created
        assert db.scalar(select(func.count()).select_from(ModerationResult)) == 0
        # Webhook delivery for failure was created
        delivery = db.scalar(select(WebhookDelivery).where(WebhookDelivery.request_id == req.id))
        assert delivery is not None
        assert delivery.event_type == "moderation.failed"


def test_asset_tenant_mismatch_terminal_failure(image_pipeline_env, monkeypatch):
    factory, storage = image_pipeline_env
    owner_id = uuid4()
    intruder_id = uuid4()
    owner = Tenant(id=owner_id, name="owner", slug="owner", status="active")
    intruder = Tenant(id=intruder_id, name="intruder", slug="intruder", status="active")
    with factory.begin() as db:
        db.add_all([owner, intruder])

    image_bytes = _make_test_image_bytes()
    object_key = f"{owner_id}/{uuid4()}.png"
    storage.put(object_key, io.BytesIO(image_bytes))

    with factory.begin() as db:
        asset = ModerationAsset(
            id=uuid4(),
            tenant_id=owner_id,
            storage_provider="local",
            object_key=object_key,
            mime_type="image/png",
            size_bytes=len(image_bytes),
        )
        db.add(asset)
        db.flush()
        # Intruder tenant tries to moderate owner's asset
        req = ModerationRequest(
            id=uuid4(),
            tenant_id=intruder_id,
            content_type="image",
            content=None,
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)

    handler = ImageModerationHandler()
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    # Must fail terminally due to PermissionError
    asyncio.run(moderation_worker.process_message(Message(req.id)))

    with factory() as db:
        stored = db.get(ModerationRequest, req.id)
        assert stored.status == "failed"
        assert "Asset does not belong to the request tenant" in stored.last_error


def test_missing_asset_id_terminal_failure(image_pipeline_env, monkeypatch):
    factory, _storage = image_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="tenant", slug="tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)
        req = ModerationRequest(
            id=uuid4(),
            tenant_id=tenant_id,
            content_type="image",
            content=None,
            asset_id=None,  # missing asset_id
            status="pending",
        )
        db.add(req)

    handler = ImageModerationHandler()
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    asyncio.run(moderation_worker.process_message(Message(req.id)))

    with factory() as db:
        stored = db.get(ModerationRequest, req.id)
        assert stored.status == "failed"
        assert "no asset" in stored.last_error


def test_unsupported_storage_provider_terminal_failure(image_pipeline_env, monkeypatch):
    factory, storage = image_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="tenant", slug="tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)
        asset = ModerationAsset(
            id=uuid4(),
            tenant_id=tenant_id,
            storage_provider="invalid-provider",
            object_key="some/key.png",
            mime_type="image/png",
            size_bytes=100,
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            id=uuid4(),
            tenant_id=tenant_id,
            content_type="image",
            content=None,
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)

    from app.services.storage.registry import get_storage_service as real_get_storage_service
    monkeypatch.setattr(
        "app.services.media.asset_resolver.get_storage_service",
        real_get_storage_service,
    )

    handler = ImageModerationHandler()
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    asyncio.run(moderation_worker.process_message(Message(req.id)))

    with factory() as db:
        stored = db.get(ModerationRequest, req.id)
        assert stored.status == "failed"
        assert "Unsupported storage provider" in stored.last_error


def test_missing_storage_object_retries_then_fails(image_pipeline_env, monkeypatch):
    factory, storage = image_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="tenant", slug="tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)
        asset = ModerationAsset(
            id=uuid4(),
            tenant_id=tenant_id,
            storage_provider="local",
            object_key="missing/file.png",  # not in storage
            mime_type="image/png",
            size_bytes=100,
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            id=uuid4(),
            tenant_id=tenant_id,
            content_type="image",
            content=None,
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)

    handler = ImageModerationHandler()
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    # Attempts 1 and 2 raise RetriableProcessingError
    for attempt in range(1, moderation_worker.MAX_RETRIES):
        with pytest.raises(moderation_worker.RetriableProcessingError):
            asyncio.run(moderation_worker.process_message(Message(req.id)))
        with factory() as db:
            stored = db.get(ModerationRequest, req.id)
            assert stored.status == "pending"
            assert stored.retry_count == attempt

    # Final attempt marks failed
    asyncio.run(moderation_worker.process_message(Message(req.id)))
    with factory() as db:
        stored = db.get(ModerationRequest, req.id)
        assert stored.status == "failed"
        assert stored.retry_count == moderation_worker.MAX_RETRIES


def test_transient_inference_error_retries_then_succeeds(image_pipeline_env, monkeypatch):
    factory, storage = image_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="tenant", slug="tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)

    image_bytes = _make_test_image_bytes()
    object_key = f"{tenant_id}/{uuid4()}.png"
    storage.put(object_key, io.BytesIO(image_bytes))

    with factory.begin() as db:
        asset = ModerationAsset(
            id=uuid4(),
            tenant_id=tenant_id,
            storage_provider="local",
            object_key=object_key,
            mime_type="image/png",
            size_bytes=len(image_bytes),
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            id=uuid4(),
            tenant_id=tenant_id,
            content_type="image",
            content=None,
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)

    attempts = 0

    class FlakyInference:
        def moderate(self, image):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("transient GPU memory blip")
            return {
                "is_flagged": False,
                "categories": [],
                "scores": {"normal": 0.99, "nsfw": 0.01},
                "model": "flaky-vit",
            }

    handler = ImageModerationHandler(inference_service=FlakyInference())
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    # First run raises RetriableProcessingError
    with pytest.raises(moderation_worker.RetriableProcessingError):
        asyncio.run(moderation_worker.process_message(Message(req.id)))

    with factory() as db:
        stored = db.get(ModerationRequest, req.id)
        assert stored.status == "pending"
        assert stored.retry_count == 1
        assert "transient GPU memory blip" in stored.last_error

    # Second run succeeds
    asyncio.run(moderation_worker.process_message(Message(req.id)))

    with factory() as db:
        stored = db.get(ModerationRequest, req.id)
        assert stored.status == "approved"
        result = db.scalar(select(ModerationResult).where(ModerationResult.request_id == req.id))
        assert result is not None
        assert result.is_flagged is False
