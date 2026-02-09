"""Database engine configuration."""

import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from alembic import command
from alembic.config import Config
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Connection pool settings
connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
async def verify_connection() -> None:
    """Attempt to connect to the database."""
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))


async def init_db() -> None:
    """Initialize database, run migrations, and verify connection."""
    try:
        logger.info("Running database migrations...")
        
        alembic_cfg_path = "alembic.ini"
        if not os.path.exists(alembic_cfg_path):
             logger.warning(f"alembic.ini not found at {alembic_cfg_path}, migrations might fail")

        # Run Alembic migrations in a separate thread to avoid asyncio loop conflicts
        alembic_cfg = Config(alembic_cfg_path)
        # IMPORTANT: Prevent Alembic from overriding our logging config
        alembic_cfg.set_main_option("script_location", "alembic")
        alembic_cfg.attributes['configure_logger'] = False
        
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
        
        logger.info("Database migrations applied successfully")

        await verify_connection()
        logger.info("Database connection verified successfully")
    except Exception as e:
        logger.critical(f"DATABASE STARTUP FAIL: {e}")
        raise RuntimeError(f"Database unavailable: {e}")


async def close_db() -> None:
    """Safe cleanup of database resources."""
    try:
        await engine.dispose()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")
