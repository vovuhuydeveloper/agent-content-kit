"""
Browser Session API — Check and manage platform login sessions.
"""

import logging
import subprocess
import sys
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("api.browser_session")

router = APIRouter(prefix="/browser-session", tags=["Browser Session"])

SUPPORTED_PLATFORMS = ["youtube", "tiktok", "facebook"]


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

    # Open browser in subprocess (non-blocking)
    try:
        subprocess.Popen(
            [sys.executable, "-m", "backend.core.browser_session", "login", platform],
            cwd=".",
        )
        return {
            "platform": platform,
            "status": "login_opened",
            "message": f"Chrome opened — login to {platform} then close the browser",
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to open browser: {e}")
