import concurrent.futures
import os
from uuid import UUID, uuid4

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.moderation import router
from app.db.base import Base
import app.db.models  # noqa: F401 - registers mapped tables
from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.moderation import ModerationRequest
from app.models.outbox import OutboxEvent
from app.models.tenant import Tenant
from app.schemas.moderation import ContentType, ModerationRequestCreate
from app.services.idempotency import compute_request_hash


@pytest.fixture
def app_env():
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
        yield client, factory, tenant_a, tenant_b, current_tenant_holder

    Base.metadata.drop_all(engine)


def test_hash_determinism():
    data1 = ModerationRequestCreate(content_type=ContentType.TEXT, content="hello world")
    data2 = ModerationRequestCreate(content_type=ContentType.TEXT, content="hello world")
    data3 = ModerationRequestCreate(content_type=ContentType.TEXT, content="different content")

    hash1 = compute_request_hash(data1)
    hash2 = compute_request_hash(data2)
    hash3 = compute_request_hash(data3)

    assert len(hash1) == 64
    assert hash1 == hash2
    assert hash1 != hash3


def test_no_idempotency_key(app_env):
    client, factory, tenant_a, _, _ = app_env

    response = client.post(
        "/api/v1/moderate/",
        json={"content_type": "text", "content": "regular request"},
    )
    assert response.status_code == 201
    res_data = response.json()
    req_uuid = UUID(res_data["id"])

    with factory() as db:
        req = db.scalar(select(ModerationRequest).where(ModerationRequest.id == req_uuid))
        assert req is not None
        assert req.idempotency_key is None
        assert req.request_hash is None

        outbox_count = db.scalar(
            select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == req_uuid)
        )
        assert outbox_count == 1


def test_first_request_with_key(app_env):
    client, factory, tenant_a, _, _ = app_env

    response = client.post(
        "/api/v1/moderate/",
        headers={"Idempotency-Key": "first-key-123"},
        json={"content_type": "text", "content": "idempotent text"},
    )
    assert response.status_code == 201
    res_data = response.json()
    req_uuid = UUID(res_data["id"])

    with factory() as db:
        req = db.scalar(select(ModerationRequest).where(ModerationRequest.id == req_uuid))
        assert req is not None
        assert req.idempotency_key == "first-key-123"
        assert req.request_hash is not None
        assert len(req.request_hash) == 64

        outbox_count = db.scalar(
            select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == req_uuid)
        )
        assert outbox_count == 1


def test_retry_same_key_same_payload(app_env):
    client, factory, tenant_a, _, _ = app_env
    key = "retry-key-001"
    payload = {"content_type": "text", "content": "repeated text"}

    resp1 = client.post("/api/v1/moderate/", headers={"Idempotency-Key": key}, json=payload)
    resp2 = client.post("/api/v1/moderate/", headers={"Idempotency-Key": key}, json=payload)

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["id"] == resp2.json()["id"]

    req_uuid = UUID(resp1.json()["id"])
    with factory() as db:
        req_count = db.scalar(
            select(func.count(ModerationRequest.id)).where(
                ModerationRequest.tenant_id == tenant_a.id,
                ModerationRequest.idempotency_key == key,
            )
        )
        assert req_count == 1

        outbox_count = db.scalar(
            select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == req_uuid)
        )
        assert outbox_count == 1


def test_same_key_different_payload_conflict(app_env):
    client, factory, tenant_a, _, _ = app_env
    key = "conflict-key-002"

    resp1 = client.post(
        "/api/v1/moderate/",
        headers={"Idempotency-Key": key},
        json={"content_type": "text", "content": "first version"},
    )
    assert resp1.status_code == 201
    req_uuid = UUID(resp1.json()["id"])

    resp2 = client.post(
        "/api/v1/moderate/",
        headers={"Idempotency-Key": key},
        json={"content_type": "text", "content": "second version"},
    )
    assert resp2.status_code == 409
    assert "already used with a different request payload" in resp2.json()["detail"]

    with factory() as db:
        req_count = db.scalar(
            select(func.count(ModerationRequest.id)).where(
                ModerationRequest.tenant_id == tenant_a.id,
                ModerationRequest.idempotency_key == key,
            )
        )
        assert req_count == 1

        outbox_count = db.scalar(
            select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == req_uuid)
        )
        assert outbox_count == 1


def test_same_key_across_different_tenants(app_env):
    client, factory, tenant_a, tenant_b, current_tenant_holder = app_env
    key = "tenant-shared-key"
    payload = {"content_type": "text", "content": "tenant text"}

    current_tenant_holder["tenant"] = tenant_a
    resp_a = client.post("/api/v1/moderate/", headers={"Idempotency-Key": key}, json=payload)
    assert resp_a.status_code == 201

    current_tenant_holder["tenant"] = tenant_b
    resp_b = client.post("/api/v1/moderate/", headers={"Idempotency-Key": key}, json=payload)
    assert resp_b.status_code == 201

    assert resp_a.json()["id"] != resp_b.json()["id"]

    with factory() as db:
        req_count = db.scalar(
            select(func.count(ModerationRequest.id)).where(
                ModerationRequest.idempotency_key == key
            )
        )
        assert req_count == 2


def test_key_length_validation(app_env):
    client, factory, tenant_a, _, _ = app_env
    long_key = "k" * 256

    response = client.post(
        "/api/v1/moderate/",
        headers={"Idempotency-Key": long_key},
        json={"content_type": "text", "content": "valid content"},
    )
    assert response.status_code == 422


def test_concurrent_identical_requests(app_env):
    client, factory, tenant_a, _, _ = app_env
    key = "concurrent-same-key"
    payload = {"content_type": "text", "content": "concurrent text"}

    def make_call():
        return client.post("/api/v1/moderate/", headers={"Idempotency-Key": key}, json=payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_call) for _ in range(5)]
        results = [f.result() for f in futures]

    status_codes = [r.status_code for r in results]
    assert all(code == 201 for code in status_codes)

    request_ids = {r.json()["id"] for r in results}
    assert len(request_ids) == 1
    winning_uuid = UUID(list(request_ids)[0])

    with factory() as db:
        req_count = db.scalar(
            select(func.count(ModerationRequest.id)).where(
                ModerationRequest.tenant_id == tenant_a.id,
                ModerationRequest.idempotency_key == key,
            )
        )
        assert req_count == 1

        outbox_count = db.scalar(
            select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == winning_uuid)
        )
        assert outbox_count == 1


def test_concurrent_different_payloads(app_env):
    client, factory, tenant_a, _, _ = app_env
    key = "concurrent-diff-key"

    def make_call(i):
        payload = {"content_type": "text", "content": f"variant {i}"}
        return client.post("/api/v1/moderate/", headers={"Idempotency-Key": key}, json=payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_call, i) for i in range(5)]
        results = [f.result() for f in futures]

    successes = [r for r in results if r.status_code == 201]
    conflicts = [r for r in results if r.status_code == 409]

    assert len(successes) == 1
    assert len(conflicts) == 4

    winning_uuid = UUID(successes[0].json()["id"])

    with factory() as db:
        req_count = db.scalar(
            select(func.count(ModerationRequest.id)).where(
                ModerationRequest.tenant_id == tenant_a.id,
                ModerationRequest.idempotency_key == key,
            )
        )
        assert req_count == 1

        outbox_count = db.scalar(
            select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == winning_uuid)
        )
        assert outbox_count == 1
