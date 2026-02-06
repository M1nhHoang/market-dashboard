"""
Database Initialization and Utilities

Functions for initializing and managing the SQLite database with SQLAlchemy.
"""
from pathlib import Path

from loguru import logger


def check_database_exists(db_path: Path) -> bool:
    """Check if database file exists."""
    return db_path.exists()


async def init_database_async() -> None:
    """
    Initialize database using SQLAlchemy.
    
    Creates all tables defined in the models.
    For development/testing only - use Alembic migrations for production.
    """
    from .session import create_tables
    await create_tables()
    logger.info("Database initialized with SQLAlchemy")


def init_database() -> None:
    """
    Sync wrapper for init_database_async.
    
    For use in sync contexts. Creates event loop if needed.
    """
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        # Already in async context, schedule as task
        asyncio.ensure_future(init_database_async())
    except RuntimeError:
        # No running loop, create one
        asyncio.run(init_database_async())


async def get_table_counts_async() -> dict:
    """
    Get row counts for all tables.
    
    Returns:
        Dict with table names and row counts
    """
    from sqlalchemy import text
    from .session import get_session
    
    tables = [
        'indicators', 'indicator_history', 'events', 'causal_analyses',
        'investigations', 'investigation_evidence', 'topic_frequency',
        'predictions', 'run_history', 'calendar_events', 'score_history'
    ]
    
    counts = {}
    async with get_session() as session:
        for table in tables:
            try:
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                counts[table] = result.scalar()
            except Exception:
                counts[table] = 0
    
    return counts


def run_migrations() -> None:
    """
    Run pending Alembic migrations.
    
    This is a convenience wrapper around Alembic upgrade command.
    """
    from alembic.config import Config
    from alembic import command
    from config import settings
    
    alembic_cfg = Config(settings.BASE_DIR / "alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations completed")


def create_migration(message: str, autogenerate: bool = True) -> None:
    """
    Create a new Alembic migration.
    
    Args:
        message: Migration description
        autogenerate: Auto-generate from model changes
    """
    from alembic.config import Config
    from alembic import command
    from config import settings
    
    alembic_cfg = Config(settings.BASE_DIR / "alembic.ini")
    command.revision(alembic_cfg, message=message, autogenerate=autogenerate)
    logger.info(f"Created migration: {message}")

