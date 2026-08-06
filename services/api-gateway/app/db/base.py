from sqlalchemy import DeclarativeBase

class Base(DeclarativeBase):
    pass

from app.models.tenant import Tenant