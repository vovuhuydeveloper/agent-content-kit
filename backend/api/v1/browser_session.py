"""
Browser Session API — Check and manage platform login sessions.
"""

import logging
import os
import subprocess
import sys
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("api.browser_session")

# Absolute project root so subprocess works regardless of uvicorn's CWD
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter(prefix="/browser-session", tags=["Browser Session"])

SUPPORTED_PLATFORMS = ["youtube", "tiktok", "facebook"]


def _is_headless_environment() -> bool:
    """Detect if running in Docker, SSH, or any environment without a display."""
    # Check Docker
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", "r") as f:
            if "docker" in f.read():
                return True
    except (FileNotFoundError, PermissionError):
        pass

    # On Linux, no DISPLAY = no GUI
    if sys.platform == "linux" and not os.environ.get("DISPLAY"):
        return True

    return False


class SessionStatus(BaseModel):
    platform: str
    connected: bool


@router.get("/status", response_model=List[SessionStatus])
def get_all_session_status():
    """Get connection status for all platforms"""
    from backend.core.browser_session import BrowserSession

    return [
        SessionStatus(platform=p, connected=BrowserSession.has_session(p))
        for p in SUPPORTED_PLATFORMS
    ]


@router.get("/{platform}/status", response_model=SessionStatus)
def get_session_status(platform: str):
    """Check if a platform has a saved browser session"""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(400, f"Unsupported platform: {platform}")

    from backend.core.browser_session import BrowserSession

    return SessionStatus(
        platform=platform, connected=BrowserSession.has_session(platform)
    )


@router.post("/{platform}/connect")
def connect_platform(platform: str):
    """
    Open Chrome for user to login.
    If already logged in → just returns connected.
    If not → opens browser, user logs in, closes browser.
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(400, f"Unsupported platform: {platform}")

    from backend.core.browser_session import BrowserSession

    # Already connected
    if BrowserSession.has_session(platform):
        return {"platform": platform, "status": "already_connected"}

    # Detect headless environment (Docker, SSH, etc.)
    is_headless = _is_headless_environment()
    if is_headless:
        cli_cmd = f"python -m backend.core.browser_session login {platform}"
        raise HTTPException(
            400,
            f"Headless environment detected (Docker/SSH) — cannot open browser UI. "
            f"Run this on your local machine first:\n\n  {cli_cmd}\n\n"
            f"Session files in data/sessions/ will be used automatically.",
        )

    # Open browser in subprocess (non-blocking)
    try:
        # Bust cache so immediate status poll returns fresh result
        BrowserSession.bust_cache(platform)

        cmd = [sys.executable, "-m", "backend.core.browser_session", "login", platform]
        logger.info(f"Launching browser subprocess: {' '.join(cmd)} (cwd={PROJECT_ROOT})")

        subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {
            "platform": platform,
            "status": "login_opened",
            "message": f"Chrome opened — login to {platform} then close the browser",
        }
    except FileNotFoundError:
        raise HTTPException(500, f"Python executable not found: {sys.executable}")
    except Exception as e:
        logger.exception(f"Failed to launch browser subprocess for {platform}")
        raise HTTPException(500, f"Failed to open browser: {type(e).__name__}: {e}")
