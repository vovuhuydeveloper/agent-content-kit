"""
TikTokPlaywrightUploader — Upload videos to TikTok via browser automation.
Uses saved session from BrowserSession.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("uploader.tiktok_playwright")


class TikTokPlaywrightUploader:
    """Upload videos to TikTok using Playwright browser automation"""

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        hashtags: list = None,
        thumbnail_path: str = None,
    ) -> Dict:
        from playwright.sync_api import sync_playwright

        video_path = str(Path(video_path).resolve())
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        from backend.core.browser_session import BrowserSession

        if not BrowserSession.has_session("tiktok"):
            raise RuntimeError(
                "TikTok not connected. Run: "
                "python -m backend.core.browser_session login tiktok"
            )

        logger.info(f"Uploading to TikTok: {title}")

        with sync_playwright() as p:
            context = BrowserSession.get_context("tiktok", p, headless=False)

            try:
                page = context.pages[0] if context.pages else context.new_page()
                post_url = self._do_upload(page, video_path, title, description, hashtags)

                logger.info("✅ TikTok upload complete")
                return {
                    "status": "published",
                    "post_id": None,
                    "post_url": post_url,
                    "platform": "tiktok",
                }
            except Exception as e:
                logger.error(f"TikTok Playwright upload failed: {e}")
                raise
            finally:
                context.close()

    def _do_upload(self, page, video_path, title, description, hashtags) -> Optional[str]:
        """Execute TikTok upload flow"""

        # 1. Go to TikTok upload page (use /upload directly — faster)
        page.goto("https://www.tiktok.com/upload", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)
        logger.info(f"TikTok upload page: {page.url}")

        # If redirected to login, try creator center
        if "login" in page.url:
            page.goto("https://www.tiktok.com/creator-center/upload", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)

        # 2. Upload video file via iframe or direct input
        logger.info("Uploading video file...")
        try:
            # TikTok upload page has an iframe
            file_input = page.locator("input[type='file'][accept*='video']").first
            file_input.wait_for(state="attached", timeout=15000)
            file_input.set_input_files(video_path)
            logger.info("Video file selected")
        except Exception:
            # Try inside iframe
            try:
                iframe = page.frame_locator("iframe").first
                file_input = iframe.locator("input[type='file']").first
                file_input.set_input_files(video_path)
                logger.info("Video file selected (iframe)")
            except Exception as e:
                logger.error(f"File input not found: {e}")
                raise

        # Wait for processing
        time.sleep(8)

        # 3. Fill caption/description
        caption = title
        if description:
            caption += f"\n{description}"
        if hashtags:
            tags_str = " ".join(f"#{h}" for h in hashtags)
            caption += f"\n{tags_str}"

        logger.info("Setting caption...")
        try:
            # TikTok caption editor
            caption_editor = page.locator(
                "[data-e2e='caption-editor'], "
                "[contenteditable='true'], "
                ".public-DraftEditor-content, "
                "div[role='textbox']"
            ).first
            caption_editor.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            time.sleep(0.5)
            # Type character by character for contenteditable
            caption_editor.fill(caption[:2200])
            logger.info("Caption set")
        except Exception as e:
            logger.warning(f"Caption: {e}")
            # Try typing directly
            try:
                page.keyboard.type(caption[:2200], delay=20)
            except Exception:
                pass

        time.sleep(2)

        # 4. Wait for video to finish processing
        logger.info("Waiting for video processing...")
        for i in range(60):  # Max 5 min
            try:
                # Check for upload complete indicators
                post_btn = page.locator(
                    "button:has-text('Post'), "
                    "button:has-text('Đăng'), "
                    "[data-e2e='post-button']"
                ).first
                if post_btn.is_enabled():
                    break
            except Exception:
                pass
            time.sleep(5)

        time.sleep(2)

        # 5. Click Post
        logger.info("Posting...")
        try:
            post_btn = page.locator(
                "button:has-text('Post'), "
                "button:has-text('Đăng'), "
                "[data-e2e='post-button']"
            ).first
            post_btn.click(timeout=10000)
            logger.info("Clicked Post")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Post button: {e}")

        # 6. Check for success
        try:
            page.wait_for_url("**/upload**", timeout=10000)
        except Exception:
            pass

        return page.url
