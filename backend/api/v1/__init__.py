"""
API v1 package for FastAPI routes.
Unified API route management — only registers modules that exist.
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

# Try importing legacy routers (may not exist in all deployments)
_optional_routers = [
    ("health", "/health", ["health"]),
    ("projects", "/projects", ["projects"]),
    ("clips", "/clips", ["clips"]),
    ("collections", "/collections", ["collections"]),
    ("tasks", "/tasks", ["tasks"]),
    ("processing", "", ["processing"]),
    ("files", "", ["files"]),
    ("settings", "/settings", ["settings"]),
    ("bilibili", "/bilibili", ["bilibili"]),
    ("youtube", "/youtube", ["youtube"]),
    ("speech_recognition", "", ["speech-recognition"]),
    ("subtitle_editor", "/subtitle-editor", ["subtitle-editor"]),
    ("upload", "", ["upload"]),
    ("progress", "/progress", ["progress"]),
    ("pipeline_control", "/pipeline", ["pipeline"]),
    ("debug", "", ["debug"]),
    ("simple_progress", "", ["simple-progress"]),
]

for module_name, prefix, tags in _optional_routers:
    try:
        mod = __import__(f"backend.api.v1.{module_name}", fromlist=["router"])
        if prefix:
            api_router.include_router(mod.router, prefix=prefix, tags=tags)
        else:
            api_router.include_router(mod.router, tags=tags)
    except (ImportError, ModuleNotFoundError):
        pass  # Module doesn't exist in this deployment

# Try legacy modules from parent package
for parent_module, tags in [("upload_queue", ["upload-queue"]), ("account_health", ["account-health"])]:
    try:
        mod = __import__(f"backend.api.{parent_module}", fromlist=["router"])
        api_router.include_router(mod.router, tags=tags)
    except (ImportError, ModuleNotFoundError):
        pass

__all__ = ["api_router"]
