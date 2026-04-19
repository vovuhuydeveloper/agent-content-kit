"""
Nango Integration — OAuth proxy for social media platforms.
Handles token management, auto-refresh, and connection status via Nango API.

Nango self-hosted replaces manual OAuth dev app setup.
Users just click "Connect" → authorize → done.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger("core.nango")


class NangoClient:
    """Client for Nango OAuth proxy API"""

    # Pre-configured provider IDs in Nango
    PROVIDERS = {
        "youtube": "google",           # Google OAuth → YouTube Data API
        "tiktok": "tiktok-accounts",    # TikTok Content API
        "facebook": "facebook",         # Facebook Graph API
        "instagram": "facebook",        # Instagram uses Facebook OAuth
    }

    SCOPES = {
        "youtube": [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        "tiktok": ["video.publish", "video.upload"],
        "facebook": [
            "pages_manage_posts",
            "pages_read_engagement",
            "publish_video",
        ],
    }

    def __init__(self):
        self.server_url = os.environ.get("NANGO_SERVER_URL", "http://localhost:3003")
        self.secret_key = os.environ.get("NANGO_SECRET_KEY", "")
        self._headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        """Check if Nango is configured"""
        return bool(self.secret_key)

    def _api(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make authenticated request to Nango API"""
        url = f"{self.server_url}{path}"
        return requests.request(method, url, headers=self._headers, timeout=10, **kwargs)

    # ─── Connection Management ───

    def get_connections(self) -> List[Dict]:
        """Get all connections"""
        try:
            resp = self._api("GET", "/connections")
            if resp.status_code == 200:
                return resp.json().get("connections", [])
        except Exception as e:
            logger.warning(f"Failed to get Nango connections: {e}")
        return []

    def get_connection(self, provider_config_key: str, connection_id: str) -> Optional[Dict]:
        """Get a specific connection with fresh tokens"""
        try:
            resp = self._api(
                "GET",
                f"/connections/{connection_id}",
                params={"provider_config_key": provider_config_key},
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"Failed to get connection {connection_id}: {e}")
        return None

    def delete_connection(self, provider_config_key: str, connection_id: str) -> bool:
        """Delete a connection"""
        try:
            resp = self._api(
                "DELETE",
                f"/connections/{connection_id}",
                params={"provider_config_key": provider_config_key},
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.warning(f"Failed to delete connection: {e}")
            return False

    # ─── Token Access ───

    def get_access_token(self, platform: str, connection_id: str = "default") -> Optional[str]:
        """
        Get fresh access token for a platform.
        Nango auto-refreshes expired tokens.
        """
        provider = self.PROVIDERS.get(platform, platform)
        conn = self.get_connection(provider, connection_id)
        if conn:
            creds = conn.get("credentials", {})
            return creds.get("access_token")
        return None

    # ─── Session Token (for frontend Connect UI) ───

    def create_connect_session(
        self,
        end_user_id: str = "default",
        allowed_integrations: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Create a Connect Session token for the frontend.
        The frontend uses this to open the Nango Connect UI.
        """
        if not self.is_configured:
            logger.warning("Nango not configured (NANGO_SECRET_KEY missing)")
            return None

        payload: Dict[str, Any] = {
            "end_user": {
                "id": end_user_id,
                "display_name": end_user_id,
            },
        }

        if allowed_integrations:
            payload["allowed_integrations"] = allowed_integrations

        try:
            resp = self._api("POST", "/connect/sessions", json=payload)
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("token")
            else:
                logger.error(f"Create session failed: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Create session failed: {e}")

        return None

    # ─── Platform Status ───

    def get_platform_status(self, connection_id: str = "default") -> Dict[str, Any]:
        """Get connection status for all platforms"""
        connections = self.get_connections()

        status = {}
        for platform, provider in self.PROVIDERS.items():
            connected = False
            saved_at = None

            for conn in connections:
                if (
                    conn.get("provider_config_key") == provider
                    and conn.get("connection_id") == connection_id
                ):
                    connected = True
                    saved_at = conn.get("created_at")
                    break

            status[platform] = {
                "connected": connected,
                "saved_at": saved_at,
                "provider": provider,
            }

        return status

    # ─── Health Check ───

    def health_check(self) -> Dict[str, Any]:
        """Check if Nango server is reachable"""
        try:
            resp = requests.get(f"{self.server_url}/health", timeout=5)
            return {
                "available": resp.status_code == 200,
                "url": self.server_url,
                "configured": self.is_configured,
            }
        except Exception:
            return {
                "available": False,
                "url": self.server_url,
                "configured": self.is_configured,
            }


# ─── Singleton ───

_nango_client: Optional[NangoClient] = None


def get_nango_client() -> NangoClient:
    global _nango_client
    if _nango_client is None:
        _nango_client = NangoClient()
    return _nango_client
