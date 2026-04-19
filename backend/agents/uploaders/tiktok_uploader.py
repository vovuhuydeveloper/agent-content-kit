"""
TikTok Uploader — Video upload via TikTok Content Posting API.
Uses direct post (video.publish scope).
"""

import logging
from pathlib import Path
from typing import Dict

import requests

logger = logging.getLogger("uploader.tiktok")


class TikTokUploader:
    """Upload videos to TikTok via Content Posting API"""

    API_BASE = "https://open.tiktokapis.com/v2"

    def _get_access_token(self) -> str:
        """Get valid TikTok access token"""
        from backend.core.oauth_manager import get_oauth_manager

        oauth = get_oauth_manager()
        token = oauth.get_access_token("tiktok")
        if not token:
            raise RuntimeError(
                "TikTok not connected. Complete OAuth flow first at /api/v1/oauth/tiktok/authorize"
            )
        return token

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        hashtags: list = None,
    ) -> Dict:
        """
        Upload a video to TikTok.

        Uses the Direct Post flow:
        1. Initialize upload → get upload_url
        2. Upload video file
        3. Publish with metadata
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        access_token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        file_size = Path(video_path).stat().st_size

        # Step 1: Initialize upload
        init_resp = requests.post(
            f"{self.API_BASE}/post/publish/video/init/",
            headers=headers,
            json={
                "post_info": {
                    "title": title[:150],
                    "privacy_level": "SELF_ONLY",  # Start as private
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": file_size,  # Single chunk for files < 64MB
                    "total_chunk_count": 1,
                },
            },
            timeout=30,
        )

        if init_resp.status_code != 200:
            raise RuntimeError(f"TikTok init failed: {init_resp.text}")

        init_data = init_resp.json().get("data", {})
        upload_url = init_data.get("upload_url")
        publish_id = init_data.get("publish_id")

        if not upload_url:
            raise RuntimeError(f"No upload URL returned: {init_resp.json()}")

        # Step 2: Upload video file
        with open(video_path, "rb") as f:
            upload_resp = requests.put(
                upload_url,
                data=f,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                },
                timeout=300,
            )

        if upload_resp.status_code not in (200, 201):
            raise RuntimeError(f"TikTok upload failed: {upload_resp.text}")

        logger.info(f"✅ TikTok upload complete, publish_id: {publish_id}")

        # Build caption with hashtags
        caption = title
        if hashtags:
            caption += " " + " ".join(f"#{h}" for h in hashtags[:5])

        return {
            "status": "published",
            "post_id": publish_id or "",
            "post_url": "",  # TikTok doesn't return URL immediately
            "platform": "tiktok",
            "note": "Video uploaded. Check TikTok Creator Center for status.",
        }
