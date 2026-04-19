"""
OAuth API — Unified OAuth endpoints.
Supports two modes:
  1. Nango mode (recommended) — 1-click connect via Nango proxy
  2. Direct mode (fallback) — manual OAuth with developer credentials

Nango mode is auto-selected when NANGO_SECRET_KEY is configured.
"""

import logging
import os
import time
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

logger = logging.getLogger("api.oauth")

router = APIRouter(prefix="/oauth", tags=["OAuth"])


# ─── Nango Mode: 1-click connect ───

class ConnectSessionResponse(BaseModel):
    mode: str  # "nango" or "direct"
    session_token: Optional[str] = None
    nango_url: Optional[str] = None
    auth_url: Optional[str] = None


@router.get("/mode", summary="Get OAuth mode")
def get_oauth_mode():
    """Check which OAuth mode is active"""
    nango_key = os.environ.get("NANGO_SECRET_KEY", "")
    nango_url = os.environ.get("NANGO_SERVER_URL", "http://localhost:3003")

    if nango_key:
        # Check if Nango is reachable
        from backend.core.nango_client import get_nango_client
        client = get_nango_client()
        health = client.health_check()
        return {
            "mode": "nango",
            "nango_available": health["available"],
            "nango_url": nango_url,
            "message": "1-click OAuth via Nango" if health["available"] else "Nango configured but unreachable",
        }

    return {
        "mode": "direct",
        "nango_available": False,
        "message": "Manual OAuth — user needs developer app credentials",
    }


@router.post("/nango/session", summary="Create Nango Connect session")
def create_nango_session():
    """Create a Nango Connect session token for the frontend"""
    from backend.core.nango_client import get_nango_client
    client = get_nango_client()

    if not client.is_configured:
        raise HTTPException(400, "Nango not configured. Set NANGO_SECRET_KEY in .env")

    token = client.create_connect_session(
        end_user_id="default",
        allowed_integrations=["google", "tiktok-accounts", "facebook"],
    )

    if not token:
        raise HTTPException(500, "Failed to create Nango session")

    nango_url = os.environ.get("NANGO_SERVER_URL", "http://localhost:3003")

    return {
        "session_token": token,
        "nango_connect_url": f"{nango_url}",
        "mode": "nango",
    }


@router.get("/nango/token/{platform}", summary="Get access token via Nango")
def get_nango_token(platform: str):
    """Get a fresh access token for a platform via Nango"""
    from backend.core.nango_client import get_nango_client
    client = get_nango_client()

    token = client.get_access_token(platform)
    if not token:
        raise HTTPException(404, f"No connection found for {platform}. Connect first.")

    return {"platform": platform, "has_token": True}


# ─── Status (works with both modes) ───

@router.get("/status", summary="Get OAuth connection status for all platforms")
def get_oauth_status():
    """Check which platforms are connected — auto-detects Nango vs Direct mode"""
    nango_key = os.environ.get("NANGO_SECRET_KEY", "")

    if nango_key:
        from backend.core.nango_client import get_nango_client
        client = get_nango_client()
        status = client.get_platform_status()
        return {"mode": "nango", **status}

    # Fallback: direct OAuth mode
    from backend.core.oauth_manager import get_oauth_manager
    oauth = get_oauth_manager()
    status = oauth.get_connection_status()
    return {"mode": "direct", **status}


@router.post("/{platform}/disconnect", summary="Disconnect a platform")
def disconnect_platform(platform: str):
    """Revoke OAuth tokens for a platform"""
    valid_platforms = ["youtube", "tiktok", "facebook", "instagram"]
    if platform not in valid_platforms:
        raise HTTPException(400, f"Unknown platform: {platform}")

    nango_key = os.environ.get("NANGO_SECRET_KEY", "")
    if nango_key:
        from backend.core.nango_client import NangoClient, get_nango_client
        client = get_nango_client()
        provider = NangoClient.PROVIDERS.get(platform, platform)
        client.delete_connection(provider, "default")
    else:
        from backend.core.oauth_manager import get_oauth_manager
        oauth = get_oauth_manager()
        oauth.delete_tokens(platform)

    return {"message": f"{platform.title()} disconnected", "platform": platform}


# ─── Direct OAuth Mode (fallback when Nango not available) ───

@router.get("/youtube/authorize", summary="Get YouTube OAuth URL (direct mode)")
def youtube_authorize(request: Request):
    """Generate YouTube OAuth authorization URL — only for direct mode"""
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(400, "YOUTUBE_CLIENT_ID not configured. Use Nango mode or set up a Google Cloud OAuth app.")

    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/oauth/youtube/callback"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
        "access_type": "offline",
        "prompt": "consent",
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/youtube/callback", summary="YouTube OAuth callback")
def youtube_callback(code: str, request: Request):
    """Handle YouTube OAuth callback (direct mode)"""
    import requests as http

    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/oauth/youtube/callback"

    resp = http.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })

    if resp.status_code != 200:
        raise HTTPException(400, f"Token exchange failed: {resp.text}")

    tokens = resp.json()
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)

    from backend.core.oauth_manager import get_oauth_manager
    oauth = get_oauth_manager()
    oauth.save_tokens("youtube", tokens)

    return RedirectResponse(url="/connections?oauth=youtube&status=success")


@router.get("/tiktok/authorize", summary="Get TikTok OAuth URL (direct mode)")
def tiktok_authorize(request: Request):
    client_key = os.environ.get("TIKTOK_CLIENT_KEY", "")
    if not client_key:
        raise HTTPException(400, "TIKTOK_CLIENT_KEY not configured. Use Nango mode or set up a TikTok Developer app.")

    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/oauth/tiktok/callback"

    params = {
        "client_key": client_key,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "video.publish,video.upload",
    }

    auth_url = f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}"
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/tiktok/callback", summary="TikTok OAuth callback")
def tiktok_callback(code: str, request: Request):
    import requests as http

    client_key = os.environ.get("TIKTOK_CLIENT_KEY", "")
    client_secret = os.environ.get("TIKTOK_CLIENT_SECRET", "")
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/oauth/tiktok/callback"

    resp = http.post("https://open.tiktokapis.com/v2/oauth/token/", data={
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    })

    if resp.status_code != 200:
        raise HTTPException(400, f"Token exchange failed: {resp.text}")

    tokens = resp.json()
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 86400)

    from backend.core.oauth_manager import get_oauth_manager
    oauth = get_oauth_manager()
    oauth.save_tokens("tiktok", tokens)

    return RedirectResponse(url="/connections?oauth=tiktok&status=success")


@router.get("/facebook/authorize", summary="Get Facebook OAuth URL (direct mode)")
def facebook_authorize(request: Request):
    app_id = os.environ.get("FACEBOOK_APP_ID", "")
    if not app_id:
        raise HTTPException(400, "FACEBOOK_APP_ID not configured. Use Nango mode or set up a Facebook Developer app.")

    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/oauth/facebook/callback"

    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "pages_manage_posts,pages_read_engagement,publish_video",
    }

    auth_url = f"https://www.facebook.com/v19.0/dialog/oauth?{urlencode(params)}"
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/facebook/callback", summary="Facebook OAuth callback")
def facebook_callback(code: str, request: Request):
    import requests as http

    app_id = os.environ.get("FACEBOOK_APP_ID", "")
    app_secret = os.environ.get("FACEBOOK_APP_SECRET", "")
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/oauth/facebook/callback"

    resp = http.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
        "client_id": app_id,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    })

    if resp.status_code != 200:
        raise HTTPException(400, f"Token exchange failed: {resp.text}")

    tokens = resp.json()

    from backend.core.oauth_manager import get_oauth_manager
    oauth = get_oauth_manager()
    oauth.save_tokens("facebook", tokens)

    return RedirectResponse(url="/connections?oauth=facebook&status=success")
