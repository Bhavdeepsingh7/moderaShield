import uuid 

from sqlalchemy import BigInteger , ForeignKey , JSON, String , Uuid
from sqlalchemy.orm import Mapped,  mapped_column , relationship

from app.db.base import Base
from app.models.base import TimeStampMixin

from app.models.moderation import ModerationRequest

class ModerationAsset(Base, TimeStampMixin):
    __tablename__ = "moderation_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("moderation_request.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    storage_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    object_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    checksum: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    asset_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    request: Mapped["ModerationRequest"] = relationship(
        "ModerationRequest",
        back_populates ="asset"
    ) 