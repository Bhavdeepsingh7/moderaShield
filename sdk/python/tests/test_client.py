import json

import httpx
import pytest

from moderashield import (
    AuthenticationError,
    MalformedResponseError,
    Moderashield,
    ModerashieldTimeoutError,
    ServerError,
)
import moderashield.client as client_module


SUBMISSION = {
    "id": "92bea38b-e1d0-4e41-a3e5-e4e8b5af9502",
    "tenant_id": "4e971a8d-e65f-485d-9cc9-2c5641457f64",
    "content_type": "text",
    "status": "pending",
}


def result(status, **extra):
    return {
        "id": SUBMISSION["id"],
        "status": status,
        "is_flagged": status == "flagged",
        "categories": ["toxic"] if status == "flagged" else [],
        "scores": {"toxic": 0.9} if status == "flagged" else {},
        "model": "moderashield-text-v1",
        "created_at": "2026-08-26T00:00:00Z",
        "updated_at": "2026-08-26T00:00:00Z",
        **extra,
    }


def mocked_client(handler):
    client = Moderashield(api_key="msk_test", poll_interval=0.01)
    client.close()
    client._client = httpx.Client(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
        headers={"X-API-Key": "msk_test"},
    )
    return client


def test_initialization_uses_environment(monkeypatch):
    monkeypatch.setenv("MODERASHIELD_API_KEY", "msk_env")
    monkeypatch.setenv("MODERASHIELD_BASE_URL", "http://api.test/")
    client = Moderashield()
    try:
        assert client.api_key == "msk_env"
        assert client.base_url == "http://api.test"
    finally:
        client.close()


def test_post_request_and_api_key_headers():
    seen = []

    def handler(request):
        seen.append(request)
        if request.method == "POST":
            assert json.loads(request.content) == {"content_type": "text", "content": "hello"}
            return httpx.Response(201, json=SUBMISSION)
        return httpx.Response(200, json=result("approved"))

    with mocked_client(handler) as client:
        assert client.moderate_text("hello").status == "approved"
    assert seen[0].url.path == "/api/v1/moderate/"
    assert seen[0].headers["x-api-key"] == "msk_test"
    assert "authorization" not in seen[0].headers


@pytest.mark.parametrize("terminal_status", ["flagged", "approved"])
def test_polls_pending_processing_to_terminal(terminal_status):
    states = iter(["pending", "processing", terminal_status])

    def handler(request):
        if request.method == "POST":
            return httpx.Response(201, json=SUBMISSION)
        return httpx.Response(200, json=result(next(states)))

    with mocked_client(handler) as client:
        response = client.moderate_text("hello")
    assert response.status == terminal_status


def test_timeout(monkeypatch):
    def handler(request):
        return httpx.Response(201, json=SUBMISSION) if request.method == "POST" else httpx.Response(200, json=result("pending"))

    clock = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(client_module.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    with mocked_client(handler) as client:
        client.timeout = 1.0
        with pytest.raises(ModerashieldTimeoutError):
            client.moderate_text("hello")


def test_authentication_and_server_errors():
    with mocked_client(lambda _: httpx.Response(401, json={"detail": "Invalid API key"})) as client:
        with pytest.raises(AuthenticationError):
            client.moderate_text("hello")
    with mocked_client(lambda _: httpx.Response(500, json={"detail": "database failure"})) as client:
        with pytest.raises(ServerError) as error:
            client.moderate_text("hello")
    assert "database failure" not in str(error.value)


def test_malformed_response_is_clean_sdk_error():
    with mocked_client(lambda _: httpx.Response(201, json={"not": "a submission"})) as client:
        with pytest.raises(MalformedResponseError):
            client.moderate_text("hello")
