import os
from io import BytesIO
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401

from app.models.moderation import ModerationRequest
from app.models.moderation_asset import ModerationAsset
from app.services.media.asset_resolver import AssetResolver


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    yield factory

    Base.metadata.drop_all(engine)


class FakeStorage:
    def __init__(self):
        self.opened_key = None

    def open(self, object_key):
        self.opened_key = object_key
        return BytesIO(b"fake image data")


def create_request_and_asset(
    factory,
    tenant_id,
    asset_tenant_id=None,
    storage_provider="local",
):
    asset = ModerationAsset(
        tenant_id=asset_tenant_id or tenant_id,
        storage_provider=storage_provider,
        object_key="tenant/file.jpg",
        mime_type="image/jpeg",
        size_bytes=16,
    )

    with factory.begin() as db:
        db.add(asset)
        db.flush()

        request = ModerationRequest(
            tenant_id=tenant_id,
            content_type="image",
            content=None,
            asset_id=asset.id,
            status="pending",
        )

        db.add(request)

    return request, asset


def test_open_asset_success(session_factory, monkeypatch):
    tenant_id = uuid4()

    request, asset = create_request_and_asset(
        session_factory,
        tenant_id,
    )

    fake_storage = FakeStorage()

    monkeypatch.setattr(
        "app.services.media.asset_resolver.get_storage_service",
        lambda provider: fake_storage,
    )

    resolver = AssetResolver()

    with session_factory() as db:
        stream = resolver.open_asset(db, request)

        assert stream.read() == b"fake image data"
        assert fake_storage.opened_key == asset.object_key


def test_missing_asset_id(session_factory):
    tenant_id = uuid4()

    request = ModerationRequest(
        tenant_id=tenant_id,
        content_type="image",
        content=None,
        asset_id=None,
        status="pending",
    )

    with session_factory.begin() as db:
        db.add(request)

    resolver = AssetResolver()

    with session_factory() as db:
        with pytest.raises(ValueError, match="no asset"):
            resolver.open_asset(db, request)


def test_asset_not_found(session_factory):
    tenant_id = uuid4()

    request = ModerationRequest(
        tenant_id=tenant_id,
        content_type="image",
        content=None,
        asset_id=uuid4(),
        status="pending",
    )

    with session_factory.begin() as db:
        db.add(request)

    resolver = AssetResolver()

    with session_factory() as db:
        with pytest.raises(FileNotFoundError, match="Asset not found"):
            resolver.open_asset(db, request)


def test_asset_tenant_mismatch(session_factory):
    request_tenant = uuid4()
    asset_tenant = uuid4()

    request, _asset = create_request_and_asset(
        session_factory,
        request_tenant,
        asset_tenant_id=asset_tenant,
    )

    resolver = AssetResolver()

    with session_factory() as db:
        with pytest.raises(
            PermissionError,
            match="does not belong to the request tenant",
        ):
            resolver.open_asset(db, request)


def test_unsupported_storage_provider(session_factory):
    tenant_id = uuid4()

    request, _asset = create_request_and_asset(
        session_factory,
        tenant_id,
        storage_provider="does-not-exist",
    )

    resolver = AssetResolver()

    with session_factory() as db:
        with pytest.raises(
            ValueError,
            match="Unsupported storage provider",
        ):
            resolver.open_asset(db, request)