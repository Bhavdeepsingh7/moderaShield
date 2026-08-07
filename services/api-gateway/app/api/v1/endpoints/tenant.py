from http.client import HTTPException

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant_service import tenant_service

router = APIRouter()

@router.post(
    "/",
    response_model=TenantResponse,
    status_code = 201,
)
def create_tenant(
    tenant: TenantCreate,
    db: Session = Depends(get_db),
):
    try:
        return tenant_service.create(
            db,
            tenant,
        )

    except ValueError as e:
        raise HTTPException(
            status_code = 400,
            detail = str(e),
        )