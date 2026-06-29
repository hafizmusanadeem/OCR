"""Structured request/response logging middleware.

Logs every HTTP request with method, path, status code, and latency
using the application's structured logging configuration.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that logs requests with timing and status.

    Example logged output:
        {
            "event": "request",
            "method": "GET",
            "path": "/health",
            "status_code": 200,
            "latency_ms": 12.5
        }
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request and log the outcome.

        Args:
            request: The incoming ASGI request.
            call_next: The next handler in the middleware chain.

        Returns:
            The ASGI response from the next handler.
        """
        start = time.perf_counter()
        response = await call_next(request)
        latency = (time.perf_counter() - start) * 1000

        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=round(latency, 3),
            client_host=request.client.host if request.client else None,
        )
        return response
