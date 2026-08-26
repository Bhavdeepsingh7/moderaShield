from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.moderation import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.models.tenant import Tenant
from app.schemas.moderation import (
    ModerationRequestCreate,
    ModerationRequestResponse,
    ModerationResultResponse,
)
from app.services.moderation_service import moderation_service

router = APIRouter()

@router.post(
    "/",
    response_model=ModerationRequestResponse,
    status_code=status.HTTP_201_CREATED,
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


@router.get("/{request_id}", response_model=ModerationResultResponse)
def get_moderation_status(
    request_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> ModerationResultResponse:
    moderation_request = db.scalar(
        select(ModerationRequest).where(
            ModerationRequest.id == request_id,
            ModerationRequest.tenant_id == tenant.id,
        )
    )

    if moderation_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )

    moderation_result = db.scalar(
        select(ModerationResult).where(ModerationResult.request_id == request_id)
    )

    return ModerationResultResponse(
        id=moderation_request.id,
        status=moderation_request.status,
        is_flagged=moderation_result.is_flagged if moderation_result else None,
        categories=moderation_result.category if moderation_result else [],
        scores=moderation_result.score if moderation_result else {},
        model=moderation_result.model if moderation_result else None,
        created_at=moderation_request.created_at,
        updated_at=moderation_request.updated_at,
    )
