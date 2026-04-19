"""
YouTube Uploader — Real video upload via YouTube Data API v3.
Uses OAuth2 with resumable upload for reliability.
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict

logger = logging.getLogger("uploader.youtube")


class YouTubeUploader:
    """Upload videos to YouTube via Data API v3"""

    def __init__(self):
        self.oauth_manager = None

    def _get_service(self):
        """Build YouTube API service with OAuth credentials"""
        from backend.core.oauth_manager import get_oauth_manager

        oauth = get_oauth_manager()
        access_token = oauth.get_access_token("youtube")

        if not access_token:
            raise RuntimeError(
                "YouTube not connected. Complete OAuth flow first at /api/v1/oauth/youtube/authorize"
            )

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        tokens = oauth.load_tokens("youtube")
        creds = Credentials(
            token=access_token,
            refresh_token=tokens.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get("YOUTUBE_CLIENT_ID", ""),
            client_secret=os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
        )

        return build("youtube", "v3", credentials=creds)

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list = None,
        thumbnail_path: str = None,
        category_id: str = "22",  # People & Blogs
        privacy: str = "private",  # private | unlisted | public
    ) -> Dict:
        """
        Upload a video to YouTube.

        Returns:
            Dict with status, post_id, post_url
        """
        from googleapiclient.http import MediaFileUpload

        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        youtube = self._get_service()

        body = {
            "snippet": {
                "title": title[:100],  # YouTube max 100 chars
                "description": description[:5000],
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10MB chunks
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        # Resumable upload with progress tracking
        response = None
        retry_count = 0
        max_retries = 3

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"YouTube upload progress: {progress}%")
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    raise RuntimeError(f"YouTube upload failed after {max_retries} retries: {e}")
                logger.warning(f"Upload error, retry {retry_count}: {e}")
                time.sleep(2 ** retry_count)

        video_id = response["id"]
        video_url = f"https://youtube.com/watch?v={video_id}"

        logger.info(f"✅ YouTube upload complete: {video_url}")

        # Upload thumbnail if provided
        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
                ).execute()
                logger.info(f"Thumbnail set for {video_id}")
            except Exception as e:
                logger.warning(f"Thumbnail upload failed: {e}")

        return {
            "status": "published",
            "post_id": video_id,
            "post_url": video_url,
            "platform": "youtube",
        }
