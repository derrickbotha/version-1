
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,          # recycle stale connections automatically
    pool_recycle=3600,           # recycle connections after 1 hour
    echo=(settings.environment == "development"),
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and ensures cleanup."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
