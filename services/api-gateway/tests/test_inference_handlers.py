import io
import pytest
from uuid import uuid4
from PIL import Image

from app.models.moderation import ModerationRequest
from app.services.inference.image_handler import ImageModerationHandler
from app.services.inference.registry import get_moderation_handler
from app.services.inference.text_handler import TextModerationHandler


def test_text_handler_is_registered():
    handler = get_moderation_handler("text")
    assert isinstance(handler, TextModerationHandler)


def test_image_handler_is_registered():
    handler = get_moderation_handler("image")
    assert isinstance(handler, ImageModerationHandler)


def test_unsupported_handler_type():
    with pytest.raises(ValueError, match="Unsupported moderation content type"):
        get_moderation_handler("audio")


def test_image_handler_resolves_asset(monkeypatch):
    request = ModerationRequest(
        tenant_id=uuid4(),
        content_type="image",
        content=None,
        status="pending",
        asset_id=uuid4(),
    )

    class FakeStream:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    stream = FakeStream()

    class FakeResolver:
        def __init__(self):
            self.called = False

        def open_asset(self, db, request):
            self.called = True
            return stream

    resolver = FakeResolver()

    monkeypatch.setattr(
        "app.services.inference.image_handler.AssetResolver",
        lambda: resolver,
    )
    monkeypatch.setattr(
        "app.services.inference.image_handler.validate_and_load_image",
        lambda s: "dummy_image",
    )

    class FakeInferenceService:
        def moderate(self, image):
            assert image == "dummy_image"
            return {
                "is_flagged": False,
                "categories": [],
                "scores": {"normal": 0.99, "nsfw": 0.01},
                "model": "fake-model",
            }

    handler = ImageModerationHandler(
        asset_resolver=resolver,
        inference_service=FakeInferenceService(),
    )

    result = handler.handle(None, request)

    assert resolver.called is True
    assert stream.closed is True
    assert result["is_flagged"] is False
    assert result["model"] == "fake-model"


def test_image_handler_closes_stream_on_validation_failure(monkeypatch):
    request = ModerationRequest(
        tenant_id=uuid4(),
        content_type="image",
        content=None,
        status="pending",
        asset_id=uuid4(),
    )

    class FakeStream:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    stream = FakeStream()

    class FakeResolver:
        def open_asset(self, db, request):
            return stream

    resolver = FakeResolver()

    def raise_error(s):
        raise ValueError("Corrupt image")

    monkeypatch.setattr(
        "app.services.inference.image_handler.validate_and_load_image",
        raise_error,
    )

    handler = ImageModerationHandler(asset_resolver=resolver)

    with pytest.raises(ValueError, match="Corrupt image"):
        handler.handle(None, request)

    assert stream.closed is True
