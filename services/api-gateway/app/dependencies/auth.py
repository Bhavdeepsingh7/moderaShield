from dataclasses import dataclass
import logging
from time import perf_counter

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.core.security import hash_api_key
from app.dependencies.database import get_db
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.repositories.api_key_repository import api_key_repository
from app.repositories.tenant_repository import tenant_repository
from app.services.api_key_cache import CachedAuthentication, api_key_authentication_cache


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    api_key: ApiKey
    tenant: Tenant


def get_current_authentication(
    raw_key: str | None = Depends(api_key_header),
    db: Session = Depends(get_db),
) -> AuthenticatedPrincipal:
    if not raw_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key")
    if not raw_key.startswith("msk_"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")

    key_hash = hash_api_key(raw_key)
    lookup_started = perf_counter()
    cached = api_key_authentication_cache.get(key_hash)
    if cached is not None:
        if cached.api_key_active and cached.tenant_status == "active":
            logger.debug(
                "API-key authentication cache=hit lookup_ms=%.2f",
                (perf_counter() - lookup_started) * 1000,
            )
            return AuthenticatedPrincipal(
                api_key=ApiKey(id=cached.api_key_id, tenant_id=cached.tenant_id, is_active=True),
                tenant=Tenant(
                    id=cached.tenant_id,
                    name=cached.tenant_name,
                    slug=cached.tenant_slug,
                    status=cached.tenant_status,
                ),
            )
        # Only successful, active authorizations are cached. This is defensive
        # for entries written by an older deployment.
        api_key_authentication_cache.invalidate(key_hash)

    api_key = api_key_repository.get_by_hash(db, key_hash)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if not api_key.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is inactive")

    tenant = tenant_repository.get_by_id(db, api_key.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant associated with the API key not found",
        )
    if tenant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant associated with the API key is not active",
        )

    api_key_authentication_cache.set(
        key_hash,
        CachedAuthentication(
            api_key_id=api_key.id,
            tenant_id=tenant.id,
            api_key_active=api_key.is_active,
            tenant_name=tenant.name,
            tenant_slug=tenant.slug,
            tenant_status=tenant.status,
        ),
    )
    logger.debug(
        "API-key authentication cache=miss database_lookup_ms=%.2f",
        (perf_counter() - lookup_started) * 1000,
    )
    return AuthenticatedPrincipal(api_key=api_key, tenant=tenant)


def get_current_api_key(
    principal: AuthenticatedPrincipal = Depends(get_current_authentication),
) -> ApiKey:
    return principal.api_key


def get_current_tenant(
    principal: AuthenticatedPrincipal = Depends(get_current_authentication),
) -> Tenant:
    return principal.tenant
