"""OCR Platform FastAPI application factory.

Bootstraps the FastAPI application with routers, middleware, CORS,
and lifespan management. On startup, creates database tables if the
PostgreSQL backend is configured.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ocr_platform.api import benchmark, health, jobs, metrics, ocr
from ocr_platform.config import settings
from ocr_platform.db.engine import DATABASE_URL, close_engine, get_engine
from ocr_platform.db.models import Base
from ocr_platform.logging_config import configure_logging, get_logger
from ocr_platform.middleware.logging import LoggingMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Configures structured logging on startup.
    - Creates database tables if PostgreSQL is configured.
    - Logs application ready state.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control to the application runtime.
    """
    configure_logging()
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        debug=settings.debug,
    )

    # Initialize database tables if configured
    if DATABASE_URL is not None:
        try:
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_initialized")
        except Exception as exc:
            logger.warning("database_init_failed", error=str(exc))

    yield

    # Shutdown
    if DATABASE_URL is not None:
        await close_engine()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI app with routers and middleware.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Distributed OCR Benchmark & Stress Testing Platform",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Structured request logging
    app.add_middleware(LoggingMiddleware)

    # Routers
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(ocr.router)
    app.include_router(jobs.router)
    app.include_router(benchmark.router)

    return app


# Uvicorn entry point
app = create_app()
