import redis.asyncio as redis

from app.core.config import settings


RATE_LIMIT_SCRIPT = """
local current = redis.call("INCR", KEYS[1])

if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end

return current
"""


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("Rate limit exceeded")


class RateLimiter:
    def __init__(self):
        self.redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

    async def check(self, tenant_id: str) -> None:
        key = f"rate_limit:{tenant_id}"

        current = await self.redis.eval(
            RATE_LIMIT_SCRIPT,
            1,
            key,
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )

        if current > settings.RATE_LIMIT_REQUESTS:
            retry_after = await self.redis.ttl(key)

            raise RateLimitExceeded(
                max(retry_after, 1)
            )

    async def close(self):
        await self.redis.aclose()