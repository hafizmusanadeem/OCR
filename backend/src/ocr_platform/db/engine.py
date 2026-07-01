"""SQLAlchemy database engine and session factory.

Provides async PostgreSQL connectivity with connection pooling.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ocr_platform.config import settings


# Convert standard postgres:// URL to async postgresql+asyncpg:// URL
def _make_async_url(url: str | None) -> str | None:
    """Convert a standard PostgreSQL URL to an async driver URL.

    Args:
        url: Standard PostgreSQL URL (e.g., ``postgres://`` or ``postgresql://``).

    Returns:
        Async-compatible URL with ``postgresql+asyncpg://`` scheme,
        or ``None`` if the input is ``None``.
    """
    if url is None:
        return None
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = _make_async_url(settings.database_url)

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    """Return the configured async SQLAlchemy engine.

    Lazily creates the engine on first call. Raises if ``database_url``
    is not configured.

    Returns:
        AsyncEngine instance.

    Raises:
        RuntimeError: If ``DATABASE_URL`` is not set.
    """
    global _engine  # noqa: PLW0603
    if _engine is None:
        if DATABASE_URL is None:
            raise RuntimeError(
                "DATABASE_URL is not configured. Set the database_url "
                "environment variable to enable persistence."
            )
        _engine = create_async_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            echo=settings.debug,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory.

    Returns:
        An ``async_sessionmaker`` bound to the engine.
    """
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def close_engine() -> None:
    """Dispose of the async engine, releasing all connections."""
    global _engine  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        _engine = None
