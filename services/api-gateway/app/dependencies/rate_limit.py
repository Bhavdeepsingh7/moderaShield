from fastapi import Depends, HTTPException, Request, status

from app.dependencies.auth import get_current_tenant
from app.models.tenant import Tenant
from app.services.rate_limiter import RateLimitExceeded


async def check_rate_limit(
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    if not rate_limiter:
        return

    try:
        await rate_limiter.check(str(tenant.id))
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(exc.retry_after),
            },
        ) from None