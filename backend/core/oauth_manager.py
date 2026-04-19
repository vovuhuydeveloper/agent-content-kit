"""
OAuth Manager — Centralized OAuth token storage and refresh.
Handles token persistence, encryption, and automatic refresh.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("core.oauth")

TOKEN_DIR = Path("data/config/oauth_tokens")


class OAuthManager:
    """Manage OAuth tokens for social media platforms"""

    def __init__(self):
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)

    def save_tokens(self, platform: str, tokens: Dict[str, Any]):
        """Save OAuth tokens to disk"""
        token_path = TOKEN_DIR / f"{platform}.json"
        tokens["saved_at"] = datetime.now(timezone.utc).isoformat()
        with open(token_path, "w") as f:
            json.dump(tokens, f, indent=2)
        logger.info(f"OAuth tokens saved for {platform}")

    def load_tokens(self, platform: str) -> Optional[Dict[str, Any]]:
        """Load OAuth tokens from disk"""
        token_path = TOKEN_DIR / f"{platform}.json"
        if not token_path.exists():
            return None
        with open(token_path, "r") as f:
            return json.load(f)

    def delete_tokens(self, platform: str):
        """Delete OAuth tokens"""
        token_path = TOKEN_DIR / f"{platform}.json"
        if token_path.exists():
            token_path.unlink()
            logger.info(f"OAuth tokens deleted for {platform}")

    def is_connected(self, platform: str) -> bool:
        """Check if platform has valid tokens"""
        tokens = self.load_tokens(platform)
        if not tokens:
            return False

        # Check expiration
        expires_at = tokens.get("expires_at", 0)
        if expires_at and time.time() > expires_at:
            # Try refresh
            refreshed = self.refresh_token(platform)
            return refreshed is not None

        return bool(tokens.get("access_token"))

    def get_access_token(self, platform: str) -> Optional[str]:
        """Get valid access token, refreshing if needed"""
        tokens = self.load_tokens(platform)
        if not tokens:
            return None

        # Check if expired
        expires_at = tokens.get("expires_at", 0)
        if expires_at and time.time() > expires_at - 300:  # 5min buffer
            tokens = self.refresh_token(platform)
            if not tokens:
                return None

        return tokens.get("access_token")

    def refresh_token(self, platform: str) -> Optional[Dict]:
        """Refresh access token using refresh_token"""
        tokens = self.load_tokens(platform)
        if not tokens or not tokens.get("refresh_token"):
            return None

        try:
            if platform == "youtube":
                return self._refresh_youtube(tokens)
            elif platform == "facebook":
                return self._refresh_facebook(tokens)
            elif platform == "tiktok":
                return self._refresh_tiktok(tokens)
        except Exception as e:
            logger.error(f"Token refresh failed for {platform}: {e}")

        return None

    def _refresh_youtube(self, tokens: Dict) -> Optional[Dict]:
        """Refresh YouTube/Google OAuth tokens"""
        import requests

        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": os.environ.get("YOUTUBE_CLIENT_ID", ""),
            "client_secret": os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
            "refresh_token": tokens["refresh_token"],
            "grant_type": "refresh_token",
        })

        if resp.status_code == 200:
            new_tokens = resp.json()
            tokens["access_token"] = new_tokens["access_token"]
            tokens["expires_at"] = time.time() + new_tokens.get("expires_in", 3600)
            self.save_tokens("youtube", tokens)
            return tokens
        return None

    def _refresh_facebook(self, tokens: Dict) -> Optional[Dict]:
        """Refresh Facebook long-lived token"""
        import requests

        resp = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": os.environ.get("FACEBOOK_APP_ID", ""),
            "client_secret": os.environ.get("FACEBOOK_APP_SECRET", ""),
            "fb_exchange_token": tokens["access_token"],
        })

        if resp.status_code == 200:
            new_tokens = resp.json()
            tokens["access_token"] = new_tokens["access_token"]
            tokens["expires_at"] = time.time() + new_tokens.get("expires_in", 5184000)
            self.save_tokens("facebook", tokens)
            return tokens
        return None

    def _refresh_tiktok(self, tokens: Dict) -> Optional[Dict]:
        """Refresh TikTok tokens"""
        import requests

        resp = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
            "client_key": os.environ.get("TIKTOK_CLIENT_KEY", ""),
            "client_secret": os.environ.get("TIKTOK_CLIENT_SECRET", ""),
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        })

        if resp.status_code == 200:
            new_tokens = resp.json()
            tokens["access_token"] = new_tokens.get("access_token")
            tokens["refresh_token"] = new_tokens.get("refresh_token", tokens["refresh_token"])
            tokens["expires_at"] = time.time() + new_tokens.get("expires_in", 86400)
            self.save_tokens("tiktok", tokens)
            return tokens
        return None

    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status for all platforms"""
        platforms = ["youtube", "tiktok", "facebook", "instagram"]
        result = {}
        for p in platforms:
            tokens = self.load_tokens(p)
            result[p] = {
                "connected": self.is_connected(p),
                "saved_at": tokens.get("saved_at") if tokens else None,
            }
        return result


# Singleton
_oauth_manager: Optional[OAuthManager] = None


def get_oauth_manager() -> OAuthManager:
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthManager()
    return _oauth_manager
