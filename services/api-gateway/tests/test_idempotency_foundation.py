import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
import app.db.models  # noqa: F401 - registers mapped tables
from app.models.moderation import ModerationRequest
from app.models.tenant import Tenant


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_moderation_request_idempotency_fields_nullable(db_session):
    tenant_id = uuid.uuid4()
    req = ModerationRequest(
        tenant_id=tenant_id,
        content_type="text/plain",
        content="hello world",
        idempotency_key=None,
        request_hash=None,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    assert req.idempotency_key is None
    assert req.request_hash is None


def test_moderation_request_idempotency_fields_populated(db_session):
    tenant_id = uuid.uuid4()
    req = ModerationRequest(
        tenant_id=tenant_id,
        content_type="text/plain",
        content="hello world",
        idempotency_key="key-12345",
        request_hash="a" * 64,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    assert req.idempotency_key == "key-12345"
    assert req.request_hash == "a" * 64


def test_multiple_null_idempotency_keys_allowed(db_session):
    tenant_id = uuid.uuid4()
    req1 = ModerationRequest(
        tenant_id=tenant_id,
        content_type="text/plain",
        content="first",
        idempotency_key=None,
    )
    req2 = ModerationRequest(
        tenant_id=tenant_id,
        content_type="text/plain",
        content="second",
        idempotency_key=None,
    )
    db_session.add(req1)
    db_session.add(req2)
    db_session.commit()

    assert req1.id is not None
    assert req2.id is not None


def test_tenant_scoped_idempotency_uniqueness_different_tenants(db_session):
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    key = "shared-key-123"

    req1 = ModerationRequest(
        tenant_id=tenant1_id,
        content_type="text/plain",
        content="content 1",
        idempotency_key=key,
    )
    req2 = ModerationRequest(
        tenant_id=tenant2_id,
        content_type="text/plain",
        content="content 2",
        idempotency_key=key,
    )
    db_session.add(req1)
    db_session.add(req2)
    db_session.commit()

    assert req1.id is not None
    assert req2.id is not None


def test_tenant_scoped_idempotency_uniqueness_same_tenant_collision(db_session):
    tenant_id = uuid.uuid4()
    key = "duplicate-key-123"

    req1 = ModerationRequest(
        tenant_id=tenant_id,
        content_type="text/plain",
        content="content 1",
        idempotency_key=key,
    )
    req2 = ModerationRequest(
        tenant_id=tenant_id,
        content_type="text/plain",
        content="content 2",
        idempotency_key=key,
    )
    db_session.add(req1)
    db_session.commit()

    db_session.add(req2)
    with pytest.raises(IntegrityError):
        db_session.commit()
