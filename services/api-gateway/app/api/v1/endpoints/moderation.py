from uuid import UUID

import logging

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
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
from app.core.config import settings
from app.services.media_service import MediaUploadTooLargeError, media_service
from app.schemas.moderation import ContentType

router = APIRouter()
logger = logging.getLogger(__name__)

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
    # Media references are server-issued upload results.  Accepting one in the
    # JSON endpoint would let a client point at another provider/object key.
    if data.media is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Media must be submitted through the media upload endpoint",
        )
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

@router.post("/media", response_model = ModerationRequestResponse, status_code = status.HTTP_201_CREATED)
async def create_media_moderation_request(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Content type is required",
        )

    mime_type = file.content_type.split(";", 1)[0].strip().lower()
    if mime_type not in settings.allowed_media_types:
        logger.info("Rejected unsupported media upload type=%s", mime_type)
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported media type",
        )

    if mime_type.startswith("image/"):
        content_type = ContentType.IMAGE

    elif mime_type.startswith("video/"):
        content_type = ContentType.VIDEO

    elif mime_type.startswith("audio/"):
        content_type = ContentType.AUDIO

    max_size_bytes = (
        settings.AUDIO_MAX_SIZE_BYTES
        if content_type == ContentType.AUDIO
        else settings.MAX_MEDIA_SIZE_BYTES
    )

    try:
        # Basic routing uses the declared MIME type. Signature validation is
        # deliberately deferred until a streaming-safe detector is selected.
        media = media_service.upload(
            file=file,
            tenant_id=tenant.id,
            max_size_bytes=max_size_bytes,
            content_type=mime_type,
        )
    except MediaUploadTooLargeError:
        logger.info("Rejected oversized media upload")
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Media upload exceeds the configured size limit",
        ) from None
    except Exception:
        logger.exception("Media storage failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to store media upload",
        ) from None

    data = ModerationRequestCreate(
        content_type = content_type,
        media = media,
    )

    try:
        return moderation_service.create_request(db, tenant, data)
    except Exception:
        db.rollback()
        # Storage and the database cannot form a distributed transaction. If
        # the DB/outbox write fails, remove the already-uploaded object.
        try:
            media_service.delete(media)
        except Exception:
            logger.exception("Failed to clean up media after database failure")
        logger.exception("Failed to create moderation request after media upload")
        raise
