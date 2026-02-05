"""
Database Session Management

Provides SQLAlchemy engine and session factory for async database access.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from loguru import logger

from config import settings
from .models import Base


# Global engine instance
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    """Get async database URL for SQLAlchemy."""
    db_path = settings.DATABASE_PATH
    return f"sqlite+aiosqlite:///{db_path}"


async def init_engine() -> AsyncEngine:
    """
    Initialize the database engine.
    
    Creates the async engine with appropriate settings.
    Called once at application startup.
    """
    global _engine, _session_factory
    
    if _engine is not None:
        return _engine
    
    database_url = get_database_url()
    logger.info(f"Initializing database engine: {database_url}")
    
    _engine = create_async_engine(
        database_url,
        echo=settings.LOG_LEVEL == "DEBUG",
        # SQLite specific settings
        connect_args={"check_same_thread": False},
    )
    
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    logger.info("Database engine initialized successfully")
    return _engine


async def close_engine() -> None:
    """Close the database engine."""
    global _engine, _session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed")


async def create_tables() -> None:
    """
    Create all tables in the database.
    
    Note: This is for development/testing only.
    Use Alembic migrations for production.
    """
    engine = await init_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def drop_tables() -> None:
    """
    Drop all tables in the database.
    
    Warning: This will delete all data!
    Use with caution.
    """
    engine = await init_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("Database tables dropped")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as async context manager.
    
    Usage:
        async with get_session() as session:
            result = await session.execute(...)
    
    The session is automatically committed on success,
    or rolled back on exception.
    """
    if _session_factory is None:
        await init_engine()
    
    session = _session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting database session.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session_dependency)):
            ...
    """
    async with get_session() as session:
        yield session


# =============================================================================
# Sync Connection (for simple read operations in API routes)
# =============================================================================
import sqlite3


def get_connection(db_path=None):
    """
    Get a synchronous SQLite connection for simple read operations.
    
    This is a simpler alternative to async sessions when you just need
    to read data and don't need ORM features.
    
    Usage:
        conn = get_connection()
        cursor = conn.execute("SELECT * FROM indicators")
        rows = cursor.fetchall()
        conn.close()
    
    Returns a connection with row_factory set to sqlite3.Row
    so you can access columns by name.
    """
    if db_path is None:
        db_path = settings.DATABASE_PATH
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
