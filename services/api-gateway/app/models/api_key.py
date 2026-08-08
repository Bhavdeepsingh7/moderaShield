import uuid
from datetime import datetime

from sqlalchemy import Boolean , DateTime , ForeignKey , String , Uuid
from sqlalchemy.orm import Mapped , mapped_column

from app.db.base import Base
from app.models.base import TimeStampMixin

class ApiKey(Base , TimeStampMixin):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key = True,
        default = uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete= "CASCADE"),
        nullable = False,
        index = True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable = False,
    )

    key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable = False,
        unique = True,
        index= True,
    )

    last_used_at : Mapped[datetime | None] = mapped_column(
        DateTime(timezone= True),
        nullable = True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable = False,
        default = True,
    )