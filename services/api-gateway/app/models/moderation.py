import uuid

from sqlalchemy import Integer, String, Text, Uuid, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped , mapped_column, relationship

from app.db.base import Base
from app.models.base import TimeStampMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.moderation_asset import ModerationAsset


class ModerationRequest(Base, TimeStampMixin):
    __tablename__ = "moderation_request"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_moderation_request_tenant_idempotency_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key = True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index = True,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    request_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable =False,
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable =True,
    )


    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default = "pending",
    )

    # A failed request has no result, so retry state belongs to the request.
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # A claim is deliberately persisted rather than kept in worker memory.  It
    # prevents a slow/stale worker from completing a request claimed by a later
    # Kafka delivery after the processing lease has expired.
    processing_token: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        index=True,
    )

    asset: Mapped["ModerationAsset | None"] = relationship(
        "ModerationAsset",
        back_populates = "requests",
    )

    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("moderation_assets.id", ondelete = "SET NULL"),
        nullable = True,
        index= True,
    )
