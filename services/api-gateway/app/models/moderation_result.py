import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON

from app.db.base import Base
from app.models.base import TimeStampMixin

class ModerationResult(Base, TimeStampMixin):
    __tablename__ = "moderation_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
        unique=True,
    )

    is_flagged: Mapped[bool] = mapped_column(
        nullable=False,
    )

    category: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default = list,
    )

    score: Mapped[dict[str, float]] = mapped_column(
        JSON,
        nullable=False,
        default= dict,
    )

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="rule-based-v1",
    )
