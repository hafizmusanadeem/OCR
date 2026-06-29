"""OCR Platform FastAPI application factory.

Bootstraps the FastAPI application with routers, middleware, CORS,
and lifespan management.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ocr_platform.api import health, metrics, ocr
from ocr_platform.config import settings
from ocr_platform.logging_config import configure_logging, get_logger
from ocr_platform.middleware.logging import LoggingMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Configures structured logging on startup.
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
    yield
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

    return app


# Uvicorn entry point
app = create_app()
