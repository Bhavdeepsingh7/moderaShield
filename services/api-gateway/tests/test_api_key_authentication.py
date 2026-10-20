import os
from uuid import UUID, uuid4

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
import fakeredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.moderation import router
from app.core.security import hash_api_key
from app.db.base import Base
import app.db.models  # noqa: F401 - registers mapped tables
from app.dependencies.database import get_db
from app.models.api_key import ApiKey
from app.models.moderation import ModerationRequest
from app.models.tenant import Tenant
from app.services.api_key_cache import api_key_authentication_cache


@pytest.fixture(autouse=True)
def isolated_api_key_cache():
    """Keep auth-cache state out of other tests and avoid a live Redis server."""
    previous_client = api_key_authentication_cache._client
    api_key_authentication_cache._client = fakeredis.FakeRedis(decode_responses=True)
    try:
        yield api_key_authentication_cache._client
    finally:
        api_key_authentication_cache._client = previous_client


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
    app.include_router(router, prefix="/api/v1/moderate")

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


def test_valid_x_api_key_creates_request_for_authenticated_tenant(client_and_session):
    client, factory = client_and_session
    tenant = create_tenant_key(factory, raw_key="msk_valid")

    response = client.post(
        "/api/v1/moderate/",
        headers={"X-API-Key": "msk_valid"},
        json={"content_type": "text", "content": "hello"},
    )

    assert response.status_code == 201
    assert response.json()["tenant_id"] == str(tenant.id)
    with factory() as db:
        request = db.get(ModerationRequest, UUID(response.json()["id"]))
        assert request.tenant_id == tenant.id


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer msk_valid"}, {"X-API-Key": "msk_missing"}],
)
def test_missing_or_invalid_x_api_key_is_rejected(client_and_session, headers):
    client, _ = client_and_session
    response = client.post(
        "/api/v1/moderate/",
        headers=headers,
        json={"content_type": "text", "content": "hello"},
    )
    assert response.status_code == 401


def test_disabled_x_api_key_is_rejected(client_and_session):
    client, factory = client_and_session
    create_tenant_key(factory, raw_key="msk_disabled", active=False)
    response = client.post(
        "/api/v1/moderate/",
        headers={"X-API-Key": "msk_disabled"},
        json={"content_type": "text", "content": "hello"},
    )
    assert response.status_code == 401


def test_tenant_cannot_retrieve_another_tenants_request(client_and_session):
    client, factory = client_and_session
    tenant_a = create_tenant_key(factory, raw_key="msk_tenant_a")
    tenant_b = create_tenant_key(factory, raw_key="msk_tenant_b")
    request = ModerationRequest(
        tenant_id=tenant_b.id,
        content_type="text",
        content="private",
        status="pending",
    )
    with factory.begin() as db:
        db.add(request)

    response = client.get(
        f"/api/v1/moderate/{request.id}",
        headers={"X-API-Key": "msk_tenant_a"},
    )
    assert response.status_code == 404


def test_valid_api_key_cache_hit_avoids_authentication_queries(client_and_session, monkeypatch):
    client, factory = client_and_session
    create_tenant_key(factory, raw_key="msk_cached")

    first = client.post(
        "/api/v1/moderate/",
        headers={"X-API-Key": "msk_cached"},
        json={"content_type": "text", "content": "first"},
    )
    assert first.status_code == 201

    import app.dependencies.auth as auth

    monkeypatch.setattr(
        auth.api_key_repository,
        "get_by_hash",
        lambda *_: pytest.fail("API-key query ran on a cache hit"),
    )
    monkeypatch.setattr(
        auth.tenant_repository,
        "get_by_id",
        lambda *_: pytest.fail("Tenant query ran on a cache hit"),
    )
    second = client.post(
        "/api/v1/moderate/",
        headers={"X-API-Key": "msk_cached"},
        json={"content_type": "text", "content": "second"},
    )
    assert second.status_code == 201


@pytest.mark.parametrize("change", ["revoked", "disabled", "rotated", "deleted"])
def test_cache_invalidation_prevents_changed_key_authentication(client_and_session, change):
    client, factory = client_and_session
    tenant = create_tenant_key(factory, raw_key="msk_rotated")
    headers = {"X-API-Key": "msk_rotated"}
    assert client.post("/api/v1/moderate/", headers=headers, json={"content_type": "text", "content": "one"}).status_code == 201

    with factory.begin() as db:
        key = db.query(ApiKey).filter(ApiKey.tenant_id == tenant.id).one()
        key_hash = key.key_hash
        if change == "deleted":
            db.delete(key)
        elif change in {"revoked", "disabled"}:
            # The current schema represents revocation by deactivation.
            key.is_active = False
        else:
            key.key_hash = hash_api_key("msk_replacement")
    api_key_authentication_cache.invalidate(key_hash)

    response = client.post("/api/v1/moderate/", headers=headers, json={"content_type": "text", "content": "two"})
    assert response.status_code == 401


def test_expired_cache_entry_falls_back_to_database(client_and_session, isolated_api_key_cache):
    client, factory = client_and_session
    create_tenant_key(factory, raw_key="msk_expired")
    headers = {"X-API-Key": "msk_expired"}
    assert client.post("/api/v1/moderate/", headers=headers, json={"content_type": "text", "content": "one"}).status_code == 201

    key_hash = hash_api_key("msk_expired")
    cache_key = api_key_authentication_cache.cache_key(key_hash)
    # Redis removes expired keys before get(); deleting here simulates that
    # post-expiry state without sleeping in the test suite.
    isolated_api_key_cache.delete(cache_key)
    assert isolated_api_key_cache.get(cache_key) is None
    assert client.post("/api/v1/moderate/", headers=headers, json={"content_type": "text", "content": "two"}).status_code == 201


def test_redis_timeout_falls_back_to_database(client_and_session, monkeypatch):
    client, factory = client_and_session
    create_tenant_key(factory, raw_key="msk_redis_timeout")

    class TimeoutRedis:
        def get(self, _key):
            import redis
            raise redis.TimeoutError("timed out")

        def set(self, *_args, **_kwargs):
            import redis
            raise redis.TimeoutError("timed out")

    monkeypatch.setattr(api_key_authentication_cache, "_client", TimeoutRedis())
    response = client.post(
        "/api/v1/moderate/",
        headers={"X-API-Key": "msk_redis_timeout"},
        json={"content_type": "text", "content": "still works"},
    )
    assert response.status_code == 201
