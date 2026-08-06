import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base
from app.models.base import TimeStampMixin

class Tenant(Base, TimeStampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        uuid.UUID(as_uuid=True),
        primary_key=True,
        default = uuid.uuid4
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable= False
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable= False,
        unique= True,
        index= True,
    )

    plan: Mapped[str] = mapped_column(
        String(255),
        default = "free"
    )

    status: Mapped[str] = mapped_column(
        String(255),
        default = "active"
    )
