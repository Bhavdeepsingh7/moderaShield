import asyncio
import json
import os
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.moderation import router
from app.db.base import Base
import app.db.models  # noqa: F401 - registers mapped tables
from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.moderation import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.models.tenant import Tenant
from app.workers import moderation_worker


class FakeInferenceService:
    def __init__(self, predict_fn):
        self.predict_fn = predict_fn

    def moderate(self, content):
        result = self.predict_fn(content)
        if "model" not in result:
            result = {**result, "model": "test-model"}
        return result


class Message:
    def __init__(self, request_id):
        self.value = json.dumps({"request_id": str(request_id)}).encode()


@pytest.fixture
def session_factory(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(moderation_worker, "SessionLocal", factory)
    yield factory
    Base.metadata.drop_all(engine)


def add_request(factory, tenant_id=None):
    request = ModerationRequest(tenant_id=tenant_id or uuid4(), content_type="text", content="text", status="pending")
    with factory.begin() as db:
        db.add(request)
    return request


def test_successful_moderation_and_duplicate_message(session_factory, monkeypatch):
    request = add_request(session_factory)
    calls = 0

    def predict(_content):
        nonlocal calls
        calls += 1
        return {"is_flagged": True, "categories": ["toxic"], "scores": {"toxic": 0.9}}

    fake_service = FakeInferenceService(predict)
    monkeypatch.setattr(moderation_worker, "get_inference_service", lambda content_type: fake_service)
    asyncio.run(moderation_worker.process_message(Message(request.id)))
    asyncio.run(moderation_worker.process_message(Message(request.id)))

    with session_factory() as db:
        assert db.get(ModerationRequest, request.id).status == "flagged"
        assert db.scalar(select(func.count()).select_from(ModerationResult)) == 1
    with pytest.raises(IntegrityError), session_factory.begin() as db:
        db.add(ModerationResult(request_id=request.id, is_flagged=False, category=[], score={}, model="test"))
    assert calls == 1


def test_failed_attempt_is_persisted_then_can_succeed(session_factory, monkeypatch):
    request = add_request(session_factory)
    outcomes = iter([RuntimeError("temporary inference error"), {"is_flagged": False, "categories": [], "scores": {}}])

    def predict(_content):
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    fake_service = FakeInferenceService(predict)
    monkeypatch.setattr(moderation_worker, "get_inference_service", lambda content_type: fake_service)
    with pytest.raises(moderation_worker.RetriableProcessingError):
        asyncio.run(moderation_worker.process_message(Message(request.id)))
    with session_factory() as db:
        stored = db.get(ModerationRequest, request.id)
        assert (stored.status, stored.retry_count, stored.last_error) == ("pending", 1, "temporary inference error")

    asyncio.run(moderation_worker.process_message(Message(request.id)))
    with session_factory() as db:
        assert db.get(ModerationRequest, request.id).status == "approved"
        assert db.scalar(select(func.count()).select_from(ModerationResult)) == 1


def test_final_failure_is_terminal_and_creates_no_result(session_factory, monkeypatch):
    request = add_request(session_factory)
    fake_service = FakeInferenceService(lambda _content: (_ for _ in ()).throw(RuntimeError("model unavailable")))
    monkeypatch.setattr(moderation_worker, "get_inference_service", lambda content_type: fake_service)

    for _ in range(moderation_worker.MAX_RETRIES - 1):
        with pytest.raises(moderation_worker.RetriableProcessingError):
            asyncio.run(moderation_worker.process_message(Message(request.id)))
    asyncio.run(moderation_worker.process_message(Message(request.id)))

    with session_factory() as db:
        stored = db.get(ModerationRequest, request.id)
        assert (stored.status, stored.retry_count, stored.last_error) == ("failed", moderation_worker.MAX_RETRIES, "model unavailable")
        assert db.scalar(select(func.count()).select_from(ModerationResult)) == 0


def test_result_retrieval_not_found_and_tenant_isolation(session_factory):
    owner = Tenant(name="owner", slug="owner", status="active")
    other = Tenant(name="other", slug="other", status="active")
    with session_factory.begin() as db:
        db.add_all([owner, other])
    request = add_request(session_factory, owner.id)
    with session_factory.begin() as db:
        db.add(ModerationResult(request_id=request.id, is_flagged=False, category=[], score={}, model="moderashield-text-v1"))
        db.get(ModerationRequest, request.id).status = "approved"

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/moderate")

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_tenant] = lambda: owner
    with TestClient(app) as client:
        assert client.get(f"/api/v1/moderate/{request.id}").status_code == 200
        assert client.get(f"/api/v1/moderate/{uuid4()}").status_code == 404

    app.dependency_overrides[get_current_tenant] = lambda: other
    with TestClient(app) as client:
        assert client.get(f"/api/v1/moderate/{request.id}").status_code == 404
