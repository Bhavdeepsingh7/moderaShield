import uuid 

from sqlalchemy import String , Text , Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimeStampMixin

class OutboxEvent(Base, TimeStampMixin):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    aggregate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable = False,
        index = True,
    )

    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )