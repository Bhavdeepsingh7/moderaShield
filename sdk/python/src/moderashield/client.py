"""Synchronous client for ModeraShield's asynchronous text moderation API."""

import os
import time
from typing import Any

import httpx
from pydantic import ValidationError

from .exceptions import (
    APIError,
    AuthenticationError,
    BadRequestError,
    MalformedResponseError,
    ModerashieldTimeoutError,
    NetworkError,
    NotFoundError,
    ServerError,
)
from .models import ModerationResult, ModerationSubmission


DEFAULT_BASE_URL = "http://localhost:8000"
TERMINAL_STATUSES = frozenset({"approved", "flagged", "failed"})


class Moderashield:
    """A synchronous ModeraShield client.

    API key and base URL may be supplied directly or via MODERASHIELD_API_KEY
    and MODERASHIELD_BASE_URL.  The client polls the existing asynchronous API
    until its request reaches ``approved``, ``flagged``, or ``failed``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        poll_interval: float = 1.0,
        timeout: float = 30.0,
        request_timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("MODERASHIELD_API_KEY")
        if not self.api_key:
            raise ValueError("api_key is required; set MODERASHIELD_API_KEY or pass api_key")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be greater than zero")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if request_timeout <= 0:
            raise ValueError("request_timeout must be greater than zero")

        resolved_base_url = base_url or os.getenv("MODERASHIELD_BASE_URL") or DEFAULT_BASE_URL
        self.base_url = resolved_base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(request_timeout, connect=min(request_timeout, 5.0)),
            headers={
                "X-API-Key": self.api_key,
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> "Moderashield":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def moderate_text(self, text: str) -> ModerationResult:
        """Submit text and return its terminal moderation result."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        submission = self._parse_submission(
            self._request("POST", "/api/v1/moderate/", json={"content_type": "text", "content": text})
        )

        deadline = time.monotonic() + self.timeout
        while True:
            result = self._parse_result(
                self._request("GET", f"/api/v1/moderate/{submission.id}")
            )
            if result.status in TERMINAL_STATUSES:
                return result
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ModerashieldTimeoutError(
                    f"Moderation request {submission.id} did not finish within {self.timeout} seconds"
                )
            time.sleep(min(self.poll_interval, remaining))

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            raise NetworkError("Request to ModeraShield timed out") from None
        except httpx.RequestError as error:
            raise NetworkError("Could not connect to ModeraShield API") from None

        if response.is_success:
            return response

        detail = self._error_detail(response)
        if response.status_code in (401, 403):
            raise AuthenticationError(detail, status_code=response.status_code)
        if response.status_code == 400 or response.status_code == 422:
            raise BadRequestError(detail, status_code=response.status_code)
        if response.status_code == 404:
            raise NotFoundError(detail, status_code=404)
        if response.status_code >= 500:
            raise ServerError("ModeraShield API encountered a server error", status_code=response.status_code)
        raise APIError(detail, status_code=response.status_code)

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return f"ModeraShield API returned HTTP {response.status_code}"
        detail = body.get("detail") if isinstance(body, dict) else None
        return detail if isinstance(detail, str) else f"ModeraShield API returned HTTP {response.status_code}"

    @staticmethod
    def _parse_submission(response: httpx.Response) -> ModerationSubmission:
        try:
            return ModerationSubmission.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise MalformedResponseError("Invalid moderation submission response") from None

    @staticmethod
    def _parse_result(response: httpx.Response) -> ModerationResult:
        try:
            return ModerationResult.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise MalformedResponseError("Invalid moderation result response") from None
