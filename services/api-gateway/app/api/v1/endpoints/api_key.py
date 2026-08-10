from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse
from app.services.api_key_service import api_key_service
from app.models.api_key import ApiKey
from app.dependencies.auth import get_current_api_key, get_current_tenant
from app.models.tenant import Tenant
router = APIRouter()

@router.post(
    "/",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    tenant_id: UUID,
    data: ApiKeyCreate,
    db: Session = Depends(get_db),
):
    try:
        api_key, raw_key = api_key_service.create_api_key(
            db, 
            tenant_id,
            data,
        )

        return {
            "id": api_key.id,
            "name": api_key.name,
            "created_at": api_key.created_at,
            "is_active": api_key.is_active,
            "key": raw_key,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/verify")
def verify_api_key(
    api_key: ApiKey = Depends(get_current_api_key),
):

    return {
        "message": "API key is valid",
        "api_key_id": str(api_key.id),
        "tenant_id": str(api_key.tenant_id),
    }


@router.get("/verify-tenant")
def verify_tenant(
    tenant: Tenant = Depends(get_current_tenant),
):
    return {
        "message": "Tenant authenticated",
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "tenant_slug": tenant.slug,
        "tenant_status": tenant.status,
            }