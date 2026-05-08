"""
PublisherAgent — Đăng video lên các nền tảng (TikTok, YouTube, Facebook, Instagram).
Supports both real OAuth upload and draft mode (when OAuth not connected).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .base import BaseAgent

logger = logging.getLogger("agent.publisher")


class PublisherAgent(BaseAgent):
    name = "PublisherAgent"
    description = "Đăng video lên TikTok, YouTube, Facebook, Instagram"
    max_retries = 2

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        approved_videos = context.get("approved_videos") or context.get("videos", [])
        scripts = context.get("scripts", [])
        thumbnails = context.get("thumbnails", [])
        platforms = context.get("platforms", ["tiktok", "youtube"])
        job_dir = Path(context["job_dir"])

        if not approved_videos:
            logger.warning("No approved videos to publish")
            return {"publications": [], "published_count": 0}

        publications = []

        for video_info in approved_videos:
            script_id = video_info.get("script_id", 1)
            video_path = video_info["path"]
            title = video_info.get("title", f"Video {script_id}")

            # Find script & thumbnail
            script = next(
                (s for s in scripts if s.get("script_id") == script_id), {}
            )
            thumbnail = next(
                (t for t in thumbnails if t.get("script_id") == script_id), {}
            )

            hashtags = script.get("hashtags", [])
            description = self._build_description(script)

            for platform in platforms:
                try:
                    result = self._publish_to_platform(
                        platform=platform,
                        video_path=video_path,
                        title=title,
                        description=description,
                        hashtags=hashtags,
                        thumbnail_path=thumbnail.get("path"),
                    )

                    publications.append({
                        "script_id": script_id,
                        "platform": platform,
                        "status": result.get("status", "pending"),
                        "post_id": result.get("post_id"),
                        "post_url": result.get("post_url"),
                        "published_at": datetime.now(timezone.utc).isoformat(),
                    })

                    # Create analytics record for published videos
                    if result.get("status") == "published":
                        try:
                            from backend.tasks.analytics_collector import create_analytics_record
                            variant = context.get("ab_variants", [{}])
                            variant_label = ""
                            for v in variant:
                                if v.get("script_id") == script_id:
                                    variant_label = v.get("variant", "")
                                    break
                            create_analytics_record.delay(
                                job_id=context.get("job_id", ""),
                                script_id=script_id,
                                platform=platform,
                                post_id=result.get("post_id", ""),
                                post_url=result.get("post_url", ""),
                                variant=variant_label,
                            )
                        except Exception as e:
                            logger.warning(f"Analytics record creation failed: {e}")

                except Exception as e:
                    logger.error(f"Failed to publish to {platform}: {e}")
                    publications.append({
                        "script_id": script_id,
                        "platform": platform,
                        "status": "failed",
                        "error": str(e),
                    })

        # Save publication records
        pub_path = job_dir / "publications.json"
        with open(pub_path, "w", encoding="utf-8") as f:
            json.dump(publications, f, ensure_ascii=False, indent=2)

        published_count = sum(1 for p in publications if p["status"] == "published")
        logger.info(
            f"Published {published_count}/{len(publications)} to {len(platforms)} platforms"
        )

        return {
            "publications": publications,
            "published_count": published_count,
        }

    def _build_description(self, script: Dict) -> str:
        """Build post description from script"""
        parts = []
        if script.get("hook"):
            parts.append(script["hook"])
        if script.get("cta"):
            parts.append(f"\n{script['cta']}")

        hashtags = script.get("hashtags", [])
        if hashtags:
            parts.append("\n" + " ".join(f"#{h}" for h in hashtags))

        return "\n".join(parts)

    def _publish_to_platform(
        self,
        platform: str,
        video_path: str,
        title: str,
        description: str,
        hashtags: list,
        thumbnail_path: str = None,
    ) -> Dict:
        """
        Publish to specific platform.
        Priority: Nango tokens → Direct OAuth → Draft mode.
        """

        if platform == "youtube":
            return self._publish_youtube(video_path, title, description, hashtags, thumbnail_path)
        elif platform == "tiktok":
            return self._publish_tiktok(video_path, title, description, hashtags)
        elif platform == "facebook":
            return self._publish_facebook(video_path, title, description)
        elif platform == "instagram":
            return self._publish_instagram(video_path, title, description)
        else:
            logger.warning(f"Unknown platform: {platform}")
            return {"status": "skipped", "reason": f"Unknown platform: {platform}"}

    def _has_token(self, platform: str) -> bool:
        """Check if platform has a valid token (Nango or direct)"""
        # Try Nango first
        try:
            from backend.core.nango_client import get_nango_client
            client = get_nango_client()
            if client.is_configured:
                token = client.get_access_token(platform)
                if token:
                    return True
        except Exception:
            pass

        # Try direct OAuth
        try:
            from backend.core.oauth_manager import get_oauth_manager
            oauth = get_oauth_manager()
            return oauth.is_connected(platform)
        except Exception:
            return False


    def _publish_youtube(self, video_path, title, description, hashtags, thumbnail_path) -> Dict:
        """YouTube upload — Playwright session → OAuth API → Draft"""

        # Priority 1: Playwright browser session (no OAuth needed)
        try:
            from backend.core.browser_session import BrowserSession
            if BrowserSession.has_session("youtube"):
                from .uploaders.youtube_playwright import YouTubePlaywrightUploader
                uploader = YouTubePlaywrightUploader()
                return uploader.upload(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=hashtags,
                    thumbnail_path=thumbnail_path,
                    privacy="PRIVATE",
                )
        except Exception as e:
            logger.warning(f"YouTube Playwright upload failed: {e}")

        # Priority 2: OAuth API token
        if self._has_token("youtube"):
            try:
                from .uploaders.youtube_uploader import YouTubeUploader
                uploader = YouTubeUploader()
                return uploader.upload(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=hashtags,
                    thumbnail_path=thumbnail_path,
                    privacy="private",
                )
            except Exception as e:
                logger.warning(f"YouTube OAuth upload failed: {e}")

        # Priority 3: Draft mode
        logger.info(f"[YouTube] Draft mode: {title}")
        return {
            "status": "draft",
            "post_id": None,
            "post_url": None,
            "note": "YouTube not connected. Run: python -m backend.core.browser_session login youtube",
        }

    def _publish_tiktok(self, video_path, title, description, hashtags) -> Dict:
        """TikTok upload — Playwright session → OAuth API → Draft"""

        # Priority 1: Playwright browser session
        try:
            from backend.core.browser_session import BrowserSession
            if BrowserSession.has_session("tiktok"):
                from .uploaders.tiktok_playwright import TikTokPlaywrightUploader
                uploader = TikTokPlaywrightUploader()
                return uploader.upload(
                    video_path=video_path,
                    title=title,
                    description=description,
                    hashtags=hashtags,
                )
        except Exception as e:
            logger.warning(f"TikTok Playwright upload failed: {e}")

        # Priority 2: OAuth API token
        if self._has_token("tiktok"):
            try:
                from .uploaders.tiktok_uploader import TikTokUploader
                uploader = TikTokUploader()
                return uploader.upload(
                    video_path=video_path,
                    title=title,
                    description=description,
                    hashtags=hashtags,
                )
            except Exception as e:
                logger.warning(f"TikTok OAuth upload failed: {e}")

        # Priority 3: Draft
        logger.info(f"[TikTok] Draft mode: {title}")
        return {
            "status": "draft",
            "post_id": None,
            "post_url": None,
            "note": "TikTok not connected. Run: python -m backend.core.browser_session login tiktok",
        }

    def _publish_facebook(self, video_path, title, description) -> Dict:
        """Facebook upload — Playwright session → OAuth API → Draft"""

        # Priority 1: Playwright browser session
        try:
            from backend.core.browser_session import BrowserSession
            if BrowserSession.has_session("facebook"):
                from .uploaders.facebook_playwright import FacebookPlaywrightUploader
                uploader = FacebookPlaywrightUploader()
                return uploader.upload(
                    video_path=video_path,
                    title=title,
                    description=description,
                    as_reel=True,
                )
        except Exception as e:
            logger.warning(f"Facebook Playwright upload failed: {e}")

        # Priority 2: OAuth API token
        if self._has_token("facebook"):
            try:
                from .uploaders.facebook_uploader import FacebookUploader
                uploader = FacebookUploader()
                return uploader.upload(
                    video_path=video_path,
                    title=title,
                    description=description,
                )
            except Exception as e:
                logger.warning(f"Facebook OAuth upload failed: {e}")

        # Priority 3: Draft
        logger.info(f"[Facebook] Draft mode: {title}")
        return {
            "status": "draft",
            "post_id": None,
            "post_url": None,
            "note": "Facebook not connected. Run: python -m backend.core.browser_session login facebook",
        }

    def _publish_instagram(self, video_path, title, description) -> Dict:
        """Instagram upload — via Facebook Graph API (requires Facebook Page)"""
        logger.info(f"[Instagram] Draft mode: {title}")
        return {
            "status": "draft",
            "post_id": None,
            "post_url": None,
            "note": "Instagram publishing requires Facebook Page connection. Go to /connections.",
        }
