"""
SQLAlchemy database session management and engine configuration.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


def get_engine():
    """Create async database engine."""
    settings = get_settings()
    db_url = settings.DATABASE_URL
    kwargs = {"echo": settings.DEBUG, "future": True}
    if not db_url.startswith("sqlite"):
        kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
        kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    return create_async_engine(db_url, **kwargs)


def get_session_factory(engine=None):
    """Create async session factory."""
    if engine is None:
        engine = get_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# Module-level references (initialized lazily)
_engine = None
_session_factory = None


def init_db():
    """Initialize database engine and session factory."""
    global _engine, _session_factory
    _engine = get_engine()
    _session_factory = get_session_factory(_engine)
    return _engine, _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session."""
    global _session_factory
    if _session_factory is None:
        init_db()

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables (for development/testing)."""
    global _engine
    if _engine is None:
        init_db()
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all tables (for testing only)."""
    global _engine
    if _engine is None:
        init_db()
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
