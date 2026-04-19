"""
Global error middleware — Centralized exception handling for FastAPI.
"""

import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("error_middleware")


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler.
    Returns a clean JSON error instead of HTML 500 page.
    """
    logger.error(
        f"Unhandled exception at {request.method} {request.url}: {exc}\n"
        f"{traceback.format_exc()}"
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if logger.isEnabledFor(logging.DEBUG) else "An unexpected error occurred",
            "path": str(request.url.path),
        },
    )
