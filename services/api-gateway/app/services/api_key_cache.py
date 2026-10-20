"""Small, fail-open Redis cache for API-key authentication data.

The cache deliberately contains only identifiers and current authorization
state.  It never contains the client API key or its database hash.
"""

import hashlib
import hmac
import json
import logging
import threading
from dataclasses import asdict, dataclass
from uuid import UUID

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "moderashield:api-key-auth:v1:"


@dataclass(frozen=True)
class CachedAuthentication:
    api_key_id: UUID
    tenant_id: UUID
    api_key_active: bool
    tenant_name: str
    tenant_slug: str
    tenant_status: str

    def as_redis_value(self) -> str:
        value = asdict(self)
        value["api_key_id"] = str(self.api_key_id)
        value["tenant_id"] = str(self.tenant_id)
        return json.dumps(value, separators=(",", ":"))

    @classmethod
    def from_redis_value(cls, value: str) -> "CachedAuthentication | None":
        try:
            payload = json.loads(value)
            return cls(
                api_key_id=UUID(payload["api_key_id"]),
                tenant_id=UUID(payload["tenant_id"]),
                api_key_active=bool(payload["api_key_active"]),
                tenant_name=str(payload["tenant_name"]),
                tenant_slug=str(payload["tenant_slug"]),
                tenant_status=str(payload["tenant_status"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Discarding malformed API-key authentication cache entry")
            return None


class ApiKeyAuthenticationCache:
    """One process-wide Redis client and bounded cache operations."""

    def __init__(self) -> None:
        self._client: redis.Redis | None = None
        self._client_lock = threading.Lock()

    def _redis(self) -> redis.Redis:
        # redis-py uses a connection pool under this one client; constructing it
        # does not create a TCP connection per request.
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    self._client = redis.Redis.from_url(
                        settings.REDIS_URL,
                        decode_responses=True,
                        socket_timeout=settings.API_KEY_CACHE_SOCKET_TIMEOUT_SECONDS,
                        socket_connect_timeout=settings.API_KEY_CACHE_SOCKET_CONNECT_TIMEOUT_SECONDS,
                        retry_on_timeout=False,
                    )
        return self._client

    @staticmethod
    def cache_key(key_hash: str) -> str:
        # HMAC prevents even the API-key SHA-256 digest being exposed in Redis
        # keys (or Redis monitoring/logging systems).
        digest = hmac.new(
            settings.SECRET_KEY.encode("utf-8"), key_hash.encode("ascii"), hashlib.sha256
        ).hexdigest()
        return f"{_CACHE_PREFIX}{digest}"

    def get(self, key_hash: str) -> CachedAuthentication | None:
        try:
            value = self._redis().get(self.cache_key(key_hash))
        except (redis.RedisError, OSError):
            logger.warning("API-key auth cache unavailable; using PostgreSQL")
            return None
        if value is None:
            return None
        return CachedAuthentication.from_redis_value(value)

    def set(self, key_hash: str, authentication: CachedAuthentication) -> None:
        try:
            self._redis().set(
                self.cache_key(key_hash),
                authentication.as_redis_value(),
                ex=settings.API_KEY_CACHE_TTL_SECONDS,
            )
        except (redis.RedisError, OSError):
            logger.warning("Could not populate API-key auth cache")

    def invalidate(self, key_hash: str) -> None:
        """Remove a key after any revoke, disable, rotate, or delete action."""
        try:
            self._redis().delete(self.cache_key(key_hash))
        except (redis.RedisError, OSError):
            logger.warning("Could not invalidate API-key auth cache entry")

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except redis.RedisError:
                logger.warning("Could not close API-key auth cache client")


api_key_authentication_cache = ApiKeyAuthenticationCache()
