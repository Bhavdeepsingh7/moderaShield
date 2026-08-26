from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.core.security import hash_api_key
from app.dependencies.database import get_db
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.repositories.api_key_repository import api_key_repository
from app.repositories.tenant_repository import tenant_repository


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_current_api_key(
        raw_key: str | None = Depends(api_key_header),
        db: Session =  Depends(get_db),

) -> ApiKey:
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key",
        )

    if not raw_key.startswith("msk_"):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid API key format",
        )

    key_hash = hash_api_key(raw_key)

    api_key = api_key_repository.get_by_hash(db, key_hash)

    if not api_key:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid API key",
        )

    if not api_key.is_active:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "API key is inactive",
        )

    return api_key


def get_current_tenant(
        api_key: ApiKey = Depends(get_current_api_key),
        db: Session = Depends(get_db),
) -> Tenant:

    tenant = tenant_repository.get_by_id(
        db,
        api_key.tenant_id,
    )

    if not tenant:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Tenant associated with the API key not found",
        )

    if tenant.status != "active":
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Tenant associated with the API key is not active",
        )

    return tenant
