import uuid
from sqlalchemy import String , Text, Uuid
from sqlalchemy.orm import Mapped , mapped_column

from app.db.base import Base
from app.models.base import TimeStampMixin

class ModerationRequest(Base, TimeStampMixin):
    __tablename__ = "moderation_request"

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


    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable =False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable =False,
    )


    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default = "pending",
    )