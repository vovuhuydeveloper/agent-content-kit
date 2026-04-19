"""
Facebook Uploader — Video upload via Facebook Graph API.
Supports Pages and personal timeline.
"""

import logging
from pathlib import Path
from typing import Dict

import requests

logger = logging.getLogger("uploader.facebook")


class FacebookUploader:
    """Upload videos to Facebook via Graph API"""

    GRAPH_API = "https://graph-video.facebook.com/v19.0"
    GRAPH_BASE = "https://graph.facebook.com/v19.0"

    def _get_access_token(self) -> str:
        """Get valid Facebook access token"""
        from backend.core.oauth_manager import get_oauth_manager

        oauth = get_oauth_manager()
        token = oauth.get_access_token("facebook")
        if not token:
            raise RuntimeError(
                "Facebook not connected. Complete OAuth flow first at /api/v1/oauth/facebook/authorize"
            )
        return token

    def _get_page_token(self, access_token: str) -> tuple:
        """Get Page access token and page ID (first page)"""
        resp = requests.get(
            f"{self.GRAPH_BASE}/me/accounts",
            params={"access_token": access_token},
            timeout=10,
        )
        if resp.status_code == 200:
            pages = resp.json().get("data", [])
            if pages:
                page = pages[0]
                return page["id"], page["access_token"]
        return None, None

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        target: str = "page",  # page | me
    ) -> Dict:
        """
        Upload video to Facebook Page or personal timeline.

        Uses resumable upload for reliability:
        1. Start upload session
        2. Upload video chunks
        3. Finish upload with metadata
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        access_token = self._get_access_token()
        file_size = Path(video_path).stat().st_size

        # Determine target
        if target == "page":
            page_id, page_token = self._get_page_token(access_token)
            if page_id:
                target_id = page_id
                token = page_token
            else:
                logger.warning("No Facebook Page found, using personal profile")
                target_id = "me"
                token = access_token
        else:
            target_id = "me"
            token = access_token

        # Step 1: Start upload session
        start_resp = requests.post(
            f"{self.GRAPH_API}/{target_id}/videos",
            data={
                "upload_phase": "start",
                "file_size": file_size,
                "access_token": token,
            },
            timeout=30,
        )

        if start_resp.status_code != 200:
            raise RuntimeError(f"Facebook upload start failed: {start_resp.text}")

        start_data = start_resp.json()
        upload_session_id = start_data["upload_session_id"]
        video_id = start_data.get("video_id", "")

        # Step 2: Upload video file
        with open(video_path, "rb") as f:
            transfer_resp = requests.post(
                f"{self.GRAPH_API}/{target_id}/videos",
                data={
                    "upload_phase": "transfer",
                    "upload_session_id": upload_session_id,
                    "start_offset": "0",
                    "access_token": token,
                },
                files={"video_file_chunk": f},
                timeout=300,
            )

        if transfer_resp.status_code != 200:
            raise RuntimeError(f"Facebook upload transfer failed: {transfer_resp.text}")

        # Step 3: Finish upload
        finish_resp = requests.post(
            f"{self.GRAPH_API}/{target_id}/videos",
            data={
                "upload_phase": "finish",
                "upload_session_id": upload_session_id,
                "title": title[:255],
                "description": description[:5000],
                "access_token": token,
            },
            timeout=30,
        )

        if finish_resp.status_code != 200:
            raise RuntimeError(f"Facebook upload finish failed: {finish_resp.text}")

        result = finish_resp.json()
        post_id = result.get("id", video_id)
        post_url = f"https://facebook.com/{post_id}" if post_id else ""

        logger.info(f"✅ Facebook upload complete: {post_url}")

        return {
            "status": "published",
            "post_id": post_id,
            "post_url": post_url,
            "platform": "facebook",
        }
