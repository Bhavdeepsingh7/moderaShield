import asyncio
import json
import os
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.webhooks import router as webhooks_router
from app.api.v1.endpoints.moderation import router as moderation_router
from app.core.security import hash_api_key
from app.db.base import Base
import app.db.models  # noqa: F401
from app.dependencies.database import get_db
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.models.webhook import Webhook, WebhookDelivery
from app.models.moderation import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.workers import moderation_worker


class FakeInferenceService:
    def __init__(self, predict_fn):
        self.predict_fn = predict_fn

    def moderate(self, content):
        result = self.predict_fn(content)
        if "model" not in result:
            result = {**result, "model": "test-model"}
        return result


from app.workers import webhook_worker


class MockResponse:
    def __init__(self, status_code, content=b""):
        self.status_code = status_code
        self.content = content
        self.request = httpx.Request("POST", "http://example.com")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client_and_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderate")
    app.include_router(webhooks_router, prefix="/api/v1/webhooks")

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, factory
    Base.metadata.drop_all(engine)


def create_tenant_key(factory, *, raw_key: str, active: bool = True):
    tenant = Tenant(name=f"tenant-{uuid4()}", slug=f"tenant-{uuid4()}", status="active")
    with factory.begin() as db:
        db.add(tenant)
        db.flush()
        db.add(ApiKey(
            tenant_id=tenant.id,
            name="test key",
            key_hash=hash_api_key(raw_key),
            is_active=active,
        ))
    return tenant


# ==========================================
# 1. API Endpoints and Isolation Tests
# ==========================================

def test_webhook_crud_and_tenant_isolation(client_and_session):
    client, factory = client_and_session
    tenant_a = create_tenant_key(factory, raw_key="msk_a")
    tenant_b = create_tenant_key(factory, raw_key="msk_b")

    # 1. Create Webhook (Tenant A)
    response = client.post(
        "/api/v1/webhooks/",
        headers={"X-API-Key": "msk_a"},
        json={"url": "https://tenant-a.com/callback"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://tenant-a.com/callback"
    assert "secret" in data
    assert len(data["secret"]) > 0
    webhook_id = data["id"]

    # 2. Get Webhook (Tenant A) - Secret should not be exposed
    response = client.get(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "msk_a"},
    )
    assert response.status_code == 200
    assert "secret" not in response.json()
    assert response.json()["url"] == "https://tenant-a.com/callback"

    # 3. List Webhooks (Tenant A) - Secret should not be exposed
    response = client.get(
        "/api/v1/webhooks/",
        headers={"X-API-Key": "msk_a"},
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert "secret" not in items[0]

    # 4. Tenant B cannot see Tenant A's webhook (returns 404, does not expose existence)
    response = client.get(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "msk_b"},
    )
    assert response.status_code == 404

    # 5. Patch Webhook (Tenant A) - Toggle enabled status
    response = client.patch(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "msk_a"},
        json={"enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    # 6. Delete Webhook (Tenant A)
    response = client.delete(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "msk_a"},
    )
    assert response.status_code == 204

    # 7. Check deletion
    response = client.get(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "msk_a"},
    )
    assert response.status_code == 404


# ==========================================
# 2. Pipeline Integration & Delivery Generation
# ==========================================

class MockMessage:
    def __init__(self, request_id):
        self.value = json.dumps({"request_id": str(request_id)}).encode()


def test_moderation_completion_creates_delivery(client_and_session, monkeypatch):
    client, factory = client_and_session
    tenant = create_tenant_key(factory, raw_key="msk_a")

    # Add webhook configuration for tenant
    with factory.begin() as db:
        db.add(Webhook(
            tenant_id=tenant.id,
            url="https://tenant-a.com/callback",
            secret="supersecret",
            enabled=True,
        ))

    # Add moderation request
    request = ModerationRequest(
        tenant_id=tenant.id,
        content_type="text",
        content="test toxic content",
        status="pending",
    )
    with factory.begin() as db:
        db.add(request)

    # Mock moderation prediction
    def mock_predict(_content):
        return {"is_flagged": True, "categories": ["toxic"], "scores": {"toxic": 0.95}}

    fake_service = FakeInferenceService(mock_predict)
    monkeypatch.setattr(moderation_worker, "SessionLocal", factory)
    monkeypatch.setattr(moderation_worker, "get_inference_service", lambda content_type: fake_service)

    # Execute moderation processing
    asyncio.run(moderation_worker.process_message(MockMessage(request.id)))

    # Verify moderation status
    with factory() as db:
        stored_request = db.get(ModerationRequest, request.id)
        assert stored_request.status == "flagged"

        # Verify webhook delivery was created atomically
        deliveries = db.scalars(select(WebhookDelivery).where(WebhookDelivery.request_id == request.id)).all()
        assert len(deliveries) == 1
        d = deliveries[0]
        assert d.status == "pending"
        assert d.event_type == "moderation.completed"
        assert d.payload["event"] == "moderation.completed"
        assert d.payload["is_flagged"] is True
        assert d.payload["categories"] == ["toxic"]


# ==========================================
# 3. Webhook Worker Delivery & Retries Tests
# ==========================================

@pytest.mark.anyio
async def test_webhook_worker_success(client_and_session, monkeypatch):
    _, factory = client_and_session
    tenant = create_tenant_key(factory, raw_key="msk_a")

    with factory.begin() as db:
        wh = Webhook(
            tenant_id=tenant.id,
            url="https://tenant-a.com/callback",
            secret="supersecret",
            enabled=True,
        )
        db.add(wh)
        db.flush()
        
        delivery = WebhookDelivery(
            webhook_id=wh.id,
            tenant_id=tenant.id,
            request_id=uuid4(),
            event_type="moderation.completed",
            payload={"event": "moderation.completed", "status": "approved"},
            status="pending",
            next_attempt_at=datetime.now(timezone.utc),
        )
        db.add(delivery)

    delivered_payloads = []

    async def mock_post(url, content, headers, timeout):
        # Verify signature in post arguments
        signature_header = headers["X-ModeraShield-Signature"]
        expected = hmac.new(b"supersecret", content, hashlib.sha256).hexdigest()
        assert signature_header == expected
        assert headers["X-ModeraShield-Event-ID"] is not None
        delivered_payloads.append(json.loads(content.decode()))
        return MockResponse(200)

    class MockAsyncClient:
        async def post(self, *args, **kwargs):
            return await mock_post(*args, **kwargs)

    db = factory()
    delivery_obj = db.scalar(select(WebhookDelivery))
    await webhook_worker.process_delivery(db, delivery_obj, MockAsyncClient())
    db.close()

    with factory() as db:
        updated = db.scalar(select(WebhookDelivery))
        assert updated.status == "delivered"
        assert updated.delivered_at is not None
        assert updated.last_error is None
        assert len(delivered_payloads) == 1


@pytest.mark.anyio
async def test_webhook_worker_5xx_retry_and_bounded_attempts(client_and_session, monkeypatch):
    _, factory = client_and_session
    tenant = create_tenant_key(factory, raw_key="msk_a")

    with factory.begin() as db:
        wh = Webhook(
            tenant_id=tenant.id,
            url="https://tenant-a.com/callback",
            secret="supersecret",
            enabled=True,
        )
        db.add(wh)
        db.flush()
        
        delivery = WebhookDelivery(
            webhook_id=wh.id,
            tenant_id=tenant.id,
            request_id=uuid4(),
            event_type="moderation.completed",
            payload={"event": "moderation.completed", "status": "approved"},
            status="pending",
            attempt_count=0,
            next_attempt_at=datetime.now(timezone.utc),
        )
        db.add(delivery)

    # 1. First attempt fails with 500
    class Mock500Client:
        async def post(self, *args, **kwargs):
            return MockResponse(500)

    db = factory()
    delivery_obj = db.scalar(select(WebhookDelivery))
    await webhook_worker.process_delivery(db, delivery_obj, Mock500Client())
    db.close()

    with factory() as db:
        updated = db.scalar(select(WebhookDelivery))
        assert updated.status == "pending"
        assert updated.attempt_count == 1
        assert "500" in updated.last_error
        next_attempt = updated.next_attempt_at.replace(tzinfo=None) if updated.next_attempt_at.tzinfo else updated.next_attempt_at
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        assert next_attempt > now_naive

    # 2. Force attempt count to max and try again to check terminal failure
    with factory.begin() as db:
        d = db.scalar(select(WebhookDelivery))
        d.attempt_count = 4  # max is 5 in settings

    db = factory()
    delivery_obj = db.scalar(select(WebhookDelivery))
    await webhook_worker.process_delivery(db, delivery_obj, Mock500Client())
    db.close()

    with factory() as db:
        updated = db.scalar(select(WebhookDelivery))
        assert updated.status == "failed"
        assert updated.attempt_count == 5
        assert "Max attempts reached" in updated.last_error


@pytest.mark.anyio
async def test_webhook_worker_4xx_permanent_failure(client_and_session):
    _, factory = client_and_session
    tenant = create_tenant_key(factory, raw_key="msk_a")

    with factory.begin() as db:
        wh = Webhook(
            tenant_id=tenant.id,
            url="https://tenant-a.com/callback",
            secret="supersecret",
            enabled=True,
        )
        db.add(wh)
        db.flush()
        
        delivery = WebhookDelivery(
            webhook_id=wh.id,
            tenant_id=tenant.id,
            request_id=uuid4(),
            event_type="moderation.completed",
            payload={"event": "moderation.completed", "status": "approved"},
            status="pending",
            next_attempt_at=datetime.now(timezone.utc),
        )
        db.add(delivery)

    class Mock400Client:
        async def post(self, *args, **kwargs):
            return MockResponse(400)

    db = factory()
    delivery_obj = db.scalar(select(WebhookDelivery))
    await webhook_worker.process_delivery(db, delivery_obj, Mock400Client())
    db.close()

    with factory() as db:
        updated = db.scalar(select(WebhookDelivery))
        assert updated.status == "failed"
        assert "400" in updated.last_error


def test_webhook_failure_does_not_rollback_moderation(client_and_session, monkeypatch):
    client, factory = client_and_session
    tenant = create_tenant_key(factory, raw_key="msk_a")

    with factory.begin() as db:
        db.add(Webhook(
            tenant_id=tenant.id,
            url="https://broken-domain.com/callback",
            secret="supersecret",
            enabled=True,
        ))

    # Trigger moderation
    request = ModerationRequest(
        tenant_id=tenant.id,
        content_type="text",
        content="some text",
        status="pending",
    )
    with factory.begin() as db:
        db.add(request)

    fake_service = FakeInferenceService(lambda x: {"is_flagged": False, "categories": [], "scores": {}})
    monkeypatch.setattr(moderation_worker, "SessionLocal", factory)
    monkeypatch.setattr(moderation_worker, "get_inference_service", lambda content_type: fake_service)

    # Run moderation worker
    asyncio.run(moderation_worker.process_message(MockMessage(request.id)))

    # Verify moderation status succeeded independently of webhook sending status
    with factory() as db:
        stored_request = db.get(ModerationRequest, request.id)
        assert stored_request.status == "approved"
        
        # Verify the webhook delivery event was still queued
        deliveries = db.scalars(select(WebhookDelivery)).all()
        assert len(deliveries) == 1
        assert deliveries[0].status == "pending"
