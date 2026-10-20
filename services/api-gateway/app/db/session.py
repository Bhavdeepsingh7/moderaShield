
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),

    # Connection pool tuning
    pool_size=20,
    max_overflow=10,
    pool_timeout=15,
    pool_pre_ping=True,
    pool_recycle=1800,
)


@event.listens_for(engine, "checkout")
def log_connection_checkout(
    dbapi_connection,
    connection_record,
    connection_proxy,
):
    logger.debug("SQLAlchemy connection checked out")


@event.listens_for(engine, "checkin")
def log_connection_checkin(
    dbapi_connection,
    connection_record,
):
    logger.debug("SQLAlchemy connection checked in")


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
