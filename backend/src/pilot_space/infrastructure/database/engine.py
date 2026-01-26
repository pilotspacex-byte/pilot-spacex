"""SQLAlchemy async engine configuration for Pilot Space.

Provides async database engine and session management for PostgreSQL via Supabase.
Uses connection pooling for efficient resource utilization.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from pilot_space.config import get_settings

if TYPE_CHECKING:
    from pilot_space.config import Settings


def create_engine(settings: "Settings | None" = None) -> AsyncEngine:
    """Create async SQLAlchemy engine with connection pooling.

    Args:
        settings: Optional settings override for testing.

    Returns:
        Configured AsyncEngine instance.
    """
    if settings is None:
        settings = get_settings()

    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_pre_ping=True,  # Verify connections before use
        echo=settings.debug,
    )


class EngineManager:
    """Singleton manager for database engine lifecycle.

    Avoids global statements by encapsulating engine state.
    """

    _instance: "EngineManager | None" = None
    _engine: AsyncEngine | None = None

    def __new__(cls) -> "EngineManager":  # noqa: PYI034 - Self not available in 3.11
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance  # type: ignore[return-value]

    def get_engine(self) -> AsyncEngine:
        """Get or create the async engine.

        Returns:
            AsyncEngine instance.
        """
        if self._engine is None:
            self._engine = create_engine()
        return self._engine

    async def dispose(self) -> None:
        """Dispose of the engine and close all connections.

        Call this during application shutdown.
        """
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None

    def reset(self) -> None:
        """Reset the manager state (for testing)."""
        self._engine = None


# Module-level manager instance
_manager = EngineManager()


def get_engine() -> AsyncEngine:
    """Get or create the global async engine.

    Returns:
        AsyncEngine instance.
    """
    return _manager.get_engine()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get async session factory.

    Returns:
        Configured async_sessionmaker.
    """
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup.

    Yields:
        AsyncSession for database operations.

    Raises:
        Exception: Re-raises any exception after rollback.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose of the global engine and close all connections.

    Call this during application shutdown.
    """
    await _manager.dispose()


async def test_connection() -> bool:
    """Test database connectivity.

    Returns:
        True if connection succeeds, False otherwise.
    """
    from sqlalchemy import text

    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1  # type: ignore[no-any-return]
    except Exception:
        return False
