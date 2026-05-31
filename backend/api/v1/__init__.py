"""
API v1 package for FastAPI routes.
"""

from fastapi import APIRouter

# Create main router
api_router = APIRouter()

# Import available route modules
from .analytics_api import router as analytics_router
from .browser_session import router as browser_session_router
from .config_api import router as config_router
from .content_jobs import router as content_jobs_router
from .oauth_api import router as oauth_router
from .schedule_api import router as schedule_router

# Register available routes
api_router.include_router(content_jobs_router, tags=["content-jobs"])
api_router.include_router(config_router, tags=["configuration"])
api_router.include_router(schedule_router, tags=["content-calendar"])
api_router.include_router(analytics_router, tags=["analytics"])
api_router.include_router(oauth_router, tags=["oauth"])
api_router.include_router(browser_session_router, tags=["browser-session"])

__all__ = ["api_router"]
