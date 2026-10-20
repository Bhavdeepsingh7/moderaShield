
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

engine_options = {
    "echo": settings.ENVIRONMENT == "development",
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}
# SQLite's default SingletonThreadPool does not accept QueuePool sizing
# arguments. Production PostgreSQL keeps the existing explicit pool settings.
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_options.update(pool_size=20, max_overflow=10, pool_timeout=15)

engine = create_engine(settings.DATABASE_URL, **engine_options)


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
