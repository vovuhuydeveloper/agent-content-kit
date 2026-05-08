"""FastAPI application entry point"""

from dotenv import load_dotenv

load_dotenv()  # Load .env BEFORE any other imports

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize Celery app early — this sets the "current app" for @shared_task decorators
# so tasks are bound to the correct Redis broker instead of defaulting to amqp://localhost
import backend.core.celery_app  # noqa

# Import configuration
from .core.config import get_api_key, get_logging_config

# Configure logging
logging_config = get_logging_config()
logging.basicConfig(
    level=getattr(logging, logging_config["level"]),
    format=logging_config["format"],
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(logging_config["file"])  # File output
    ]
)

logger = logging.getLogger(__name__)

# Unified API route registration
from .api.v1 import api_router
from .core.database import engine
from .models.base import Base

# Create FastAPI app
app = FastAPI(
    title="AutoClip API",
    description="AI Video Content Pipeline API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Create database tables
@app.on_event("startup")
async def startup_event():
    logger.info("Starting API server...")
    # Import all models to ensure tables are created
    try:
        from .models.bilibili import BilibiliAccount, UploadRecord
    except ImportError:
        pass
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    # Loading API key to environment
    api_key = get_api_key()
    if api_key:
        import os
        os.environ["DASHSCOPE_API_KEY"] = api_key
        logger.info("API key loaded to environment")
    else:
        logger.warning("API key configuration not found")

    # WebSocket gateway disabled, using simple progress system
    logger.info("WebSocket gateway disabled, using simple progress system")

    # Start Telegram bot polling (handles approve/reject callbacks)
    try:
        from .telegram_bot import start_telegram_bot
        start_telegram_bot()
        logger.info("Telegram bot polling started")
    except Exception as e:
        logger.warning(f"Telegram bot failed to start: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down API server...")
    # WebSocket gateway disabled
    # from .services.websocket_gateway_service import websocket_gateway_service
    # await websocket_gateway_service.stop()
    # logger.info("WebSocket gateway stopped")
    logger.info("WebSocket gateway disabled")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include unified API routes
app.include_router(api_router, prefix="/api/v1")

# Serve dashboard static files (production build)
import os

from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "dist")

# Root redirect — vào dashboard nếu đã có job, setup nếu chưa
@app.get("/")
async def root_redirect():
    from .core.database import SessionLocal
    from .models.content_job import ContentJob
    try:
        db = SessionLocal()
        has_jobs = db.query(ContentJob).first() is not None
        db.close()
        if has_jobs:
            return RedirectResponse(url="/dashboard", status_code=302)
    except Exception:
        pass
    return RedirectResponse(url="/setup", status_code=302)

dashboard_assets_dir = os.path.join(dashboard_dir, "assets")
dashboard_index = os.path.join(dashboard_dir, "index.html")

if os.path.exists(dashboard_index):
    # Mount assets only if the directory exists
    if os.path.exists(dashboard_assets_dir):
        app.mount("/assets", StaticFiles(directory=dashboard_assets_dir), name="dashboard-assets")

    @app.get("/setup")
    @app.get("/setup/{path:path}")
    @app.get("/dashboard")
    @app.get("/dashboard/{path:path}")
    @app.get("/jobs/{path:path}")
    @app.get("/calendar")
    @app.get("/analytics")
    @app.get("/connections")
    @app.get("/connect")
    @app.get("/connect/{path:path}")
    async def serve_dashboard():
        return FileResponse(dashboard_index)

    # Serve favicon if exists
    favicon_path = os.path.join(dashboard_dir, "favicon.ico")
    if os.path.exists(favicon_path):
        @app.get("/favicon.ico")
        async def favicon():
            return FileResponse(favicon_path)

    logger.info(f"Dashboard served from {dashboard_dir}")
else:
    # No dashboard build — redirect all UI routes to API docs
    @app.get("/setup")
    @app.get("/dashboard")
    @app.get("/calendar")
    @app.get("/analytics")
    @app.get("/connections")
    async def no_dashboard():
        return RedirectResponse(url="/docs", status_code=302)
    logger.info("Dashboard not built — run 'cd dashboard && npm run build'")

# Video categories endpoint
@app.get("/api/v1/video-categories")
async def get_video_categories():
    """getVideo category configuration."""
    return {
        "categories": [
            {
                "value": "default",
                "name": "Default",
                "description": "General video contentprocessing",
                "icon": "🎬",
                "color": "#4facfe"
            },
            {
                "value": "knowledge",
                "name": "Educational",
                "description": "、、、",
                "icon": "📚",
                "color": "#52c41a"
            },
            {
                "value": "entertainment",
                "name": "",
                "description": "、、",
                "icon": "🎮",
                "color": "#722ed1"
            },
            {
                "value": "business",
                "name": "",
                "description": "、、",
                "icon": "💼",
                "color": "#fa8c16"
            },
            {
                "value": "experience",
                "name": "",
                "description": "、",
                "icon": "🌟",
                "color": "#eb2f96"
            },
            {
                "value": "opinion",
                "name": "",
                "description": "、",
                "icon": "💭",
                "color": "#13c2c2"
            },
            {
                "value": "speech",
                "name": "",
                "description": "Public speeches and lectures",
                "icon": "🎤",
                "color": "#f5222d"
            }
        ]
    }

# Import unified errormiddleware
from .core.error_middleware import global_exception_handler

# Register global exceptionhandler
app.add_exception_handler(Exception, global_exception_handler)

if __name__ == "__main__":
    import sys

    import uvicorn

    # Defaultport
    port = 8000

    # Check CLI arguments
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    logger.error(f"Invalid port number: {sys.argv[i + 1]}")
                    port = 8000

    logger.info(f"Starting server, port，port: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
