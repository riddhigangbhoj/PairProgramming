"""
Database configuration and session management.
Sets up SQLAlchemy engine and provides database session dependency.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings


# Database engine configuration
def get_engine_config():
    """
    Get database engine configuration based on database type.
    Applies specific optimizations for PostgreSQL and SQLite.
    """
    config = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,  # Verify connections before using them
    }

    if "sqlite" in settings.DATABASE_URL:
        # SQLite specific configuration
        config["connect_args"] = {"check_same_thread": False}
    elif "postgresql" in settings.DATABASE_URL:
        # PostgreSQL specific configuration for production
        config["pool_size"] = 10  # Maximum connections in pool
        config["max_overflow"] = 20  # Extra connections beyond pool_size
        config["pool_timeout"] = 30  # Seconds to wait for connection
        config["pool_recycle"] = 3600  # Recycle connections after 1 hour

    return config


# Create database engine
engine = create_engine(settings.DATABASE_URL, **get_engine_config())

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency for getting database session
def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Automatically closes the session after the request.
    
    Usage in FastAPI:
        @app.get("/rooms")
        def get_rooms(db: Session = Depends(get_db)):
            return db.query(Room).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    Call this on application startup.
    """
    from app.models import Base
    Base.metadata.create_all(bind=engine)