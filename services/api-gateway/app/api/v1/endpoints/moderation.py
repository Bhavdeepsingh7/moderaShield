from fastapi import APIRouter , Depends , status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal

from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.tenant import Tenant
from app.models.moderation import ModerationRequest
from app.schemas.moderation import (ModerationRequestCreate, ModerationRequestResponse)
from app.services.moderation_service import moderation_service
from schemas.moderation_status import ModerationStatusResponse

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
    return moderation_service.create_request(
        db,
        tenant,
        data,
    )


@router.get(
    "/{request_id}",
    response_model = ModerationStatusResponse,
)
def get_moderation_status(request_id: str):

    db = SessionLocal()

    try:
        moderation_request = db.scalar(
            select(ModerationRequest).where(
                ModerationRequest.id == request_id
            )
        )

        if moderation_request is None:
            raise HTTPException(
                status_code = 404,
                detail="Request not found",
            )

        return moderation_request

    finally:
        db.close()