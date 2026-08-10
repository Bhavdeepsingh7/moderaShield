from fastapi import APIRouter , Depends , status, HTTPException
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.tenant import Tenant
from app.schemas.moderation import (ModerationRequestCreate, ModerationRequestResponse)
from app.services.moderation_service import moderation_service

router = APIRouter()

@router.post(
    "/",
    response_model = ModerationRequestResponse,
    status_code = status.HTTP_201_CREATED,
)
async def create_moderation_request(
    data: ModerationRequestCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return await moderation_service.create_request(
        db,
        tenant,
        data,
    )