import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.metrics import router
from app.core.security import hash_api_key
from app.db.base import Base
import app.db.models  # noqa: F401 - registers mapped tables
from app.dependencies.database import get_db
from app.models.api_key import ApiKey
from app.models.moderation import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.models.tenant import Tenant


@pytest.fixture
def metrics_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/metrics")

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


def make_tenant(factory, key):
    tenant = Tenant(name=f"tenant-{uuid4()}", slug=f"tenant-{uuid4()}", status="active")
    with factory.begin() as db:
        db.add(tenant)
        db.flush()
        db.add(ApiKey(tenant_id=tenant.id, name="metrics", key_hash=hash_api_key(key), is_active=True))
    return tenant


def add_request(factory, tenant, status, *, categories=None, created_at=None, content="sensitive source text"):
    created_at = created_at or datetime.now(timezone.utc)
    request = ModerationRequest(
        tenant_id=tenant.id,
        content_type="text",
        content=content,
        status=status,
        created_at=created_at,
        updated_at=created_at,
    )
    with factory.begin() as db:
        db.add(request)
        db.flush()
        if categories is not None:
            db.add(ModerationResult(
                request_id=request.id,
                is_flagged=bool(categories),
                category=categories,
                score={},
                model="moderashield-text-v1",
                created_at=created_at,
                updated_at=created_at,
            ))
    return request


def headers(key="msk_a"):
    return {"X-API-Key": key}


def test_overview_handles_zero_and_actual_statuses(metrics_client):
    client, factory = metrics_client
    tenant = make_tenant(factory, "msk_a")
    assert client.get("/api/v1/metrics/overview", headers=headers()).json() == {
        "total_requests": 0, "approved_requests": 0, "flagged_requests": 0,
        "failed_requests": 0, "flag_rate": 0.0,
    }
    add_request(factory, tenant, "approved", categories=[])
    add_request(factory, tenant, "flagged", categories=["toxic"])
    add_request(factory, tenant, "failed")
    response = client.get("/api/v1/metrics/overview", headers=headers())
    assert response.json() == {
        "total_requests": 3, "approved_requests": 1, "flagged_requests": 1,
        "failed_requests": 1, "flag_rate": pytest.approx(1 / 3),
    }
    assert client.get("/api/v1/metrics/breakdown", headers=headers()).json()["statuses"] == {
        "approved": 1, "failed": 1, "flagged": 1,
    }


def test_categories_count_each_stored_category_and_are_tenant_scoped(metrics_client):
    client, factory = metrics_client
    tenant_a = make_tenant(factory, "msk_a")
    tenant_b = make_tenant(factory, "msk_b")
    add_request(factory, tenant_a, "flagged", categories=["toxic", "threat"])
    add_request(factory, tenant_a, "flagged", categories=["toxic"])
    add_request(factory, tenant_b, "flagged", categories=["identity_hate"])
    response = client.get("/api/v1/metrics/categories", headers=headers())
    assert response.json() == {"categories": {"threat": 1, "toxic": 2}}


def test_usage_is_utc_daily_tenant_scoped_and_zero_filled(metrics_client):
    client, factory = metrics_client
    tenant_a = make_tenant(factory, "msk_a")
    tenant_b = make_tenant(factory, "msk_b")
    now = datetime.now(timezone.utc)
    add_request(factory, tenant_a, "approved", created_at=now - timedelta(days=2), categories=[])
    add_request(factory, tenant_a, "flagged", created_at=now, categories=["toxic"])
    add_request(factory, tenant_b, "failed", created_at=now, categories=[])
    days = client.get("/api/v1/metrics/usage?days=3", headers=headers()).json()["days"]
    assert [day["requests"] for day in days] == [1, 0, 1]
    assert [day["approved"] for day in days] == [1, 0, 0]
    assert [day["flagged"] for day in days] == [0, 0, 1]
    assert [day["failed"] for day in days] == [0, 0, 0]


@pytest.mark.parametrize("path", ["/api/v1/metrics/usage?days=0", "/api/v1/metrics/usage?days=91", "/api/v1/metrics/requests?page=0", "/api/v1/metrics/requests?page_size=101"])
def test_invalid_usage_or_pagination_is_rejected(metrics_client, path):
    client, factory = metrics_client
    make_tenant(factory, "msk_a")
    assert client.get(path, headers=headers()).status_code == 422


def test_recent_requests_are_paginated_tenant_scoped_and_never_expose_content(metrics_client):
    client, factory = metrics_client
    tenant_a = make_tenant(factory, "msk_a")
    tenant_b = make_tenant(factory, "msk_b")
    oldest = add_request(factory, tenant_a, "approved", categories=[], created_at=datetime.now(timezone.utc) - timedelta(minutes=2), content="do not expose")
    newest = add_request(factory, tenant_a, "flagged", categories=["threat"], created_at=datetime.now(timezone.utc) - timedelta(minutes=1), content="do not expose either")
    add_request(factory, tenant_b, "flagged", categories=["toxic"])
    response = client.get("/api/v1/metrics/requests?page=1&page_size=1", headers=headers())
    payload = response.json()
    assert (payload["total"], payload["page"], payload["page_size"]) == (2, 1, 1)
    assert payload["items"][0]["id"] == str(newest.id)
    assert "content" not in payload["items"][0]
    assert "key" not in str(payload).lower()
    second_page = client.get("/api/v1/metrics/requests?page=2&page_size=1", headers=headers()).json()
    assert second_page["items"][0]["id"] == str(oldest.id)
