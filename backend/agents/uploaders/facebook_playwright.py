"""
FacebookPlaywrightUploader — Upload videos/reels to Facebook via browser automation.
Uses saved session from BrowserSession.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("uploader.facebook_playwright")


class FacebookPlaywrightUploader:
    """Upload videos to Facebook using Playwright browser automation"""

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        as_reel: bool = True,
    ) -> Dict:
        from playwright.sync_api import sync_playwright

        video_path = str(Path(video_path).resolve())
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        from backend.core.browser_session import BrowserSession

        if not BrowserSession.has_session("facebook"):
            raise RuntimeError(
                "Facebook not connected. Run: "
                "python -m backend.core.browser_session login facebook"
            )

        logger.info(f"Uploading to Facebook: {title}")

        with sync_playwright() as p:
            context = BrowserSession.get_context("facebook", p, headless=False)

            try:
                page = context.pages[0] if context.pages else context.new_page()
                post_url = self._do_upload(page, video_path, title, description, as_reel)

                logger.info("✅ Facebook upload complete")
                return {
                    "status": "published",
                    "post_id": None,
                    "post_url": post_url,
                    "platform": "facebook",
                }
            except Exception as e:
                logger.error(f"Facebook Playwright upload failed: {e}")
                raise
            finally:
                context.close()

    def _do_upload(self, page, video_path, title, description, as_reel) -> Optional[str]:
        """Execute Facebook upload flow"""

        if as_reel:
            return self._upload_reel(page, video_path, title, description)
        else:
            return self._upload_video_post(page, video_path, title, description)

    def _upload_reel(self, page, video_path, title, description) -> Optional[str]:
        """Upload as Facebook Reel"""

        # 1. Go to Reel creation page
        page.goto("https://www.facebook.com/reels/create", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)
        logger.info(f"Facebook Reel page: {page.url}")

        # 2. Upload video
        logger.info("Uploading video file...")
        try:
            file_input = page.locator("input[type='file'][accept*='video']").first
            file_input.wait_for(state="attached", timeout=20000)
            file_input.set_input_files(video_path)
            logger.info("Video file selected")
        except Exception as e:
            logger.error(f"File input not found: {e}")
            raise

        time.sleep(8)

        # 3. Click Next if needed
        try:
            next_btn = page.locator(
                "div[role='button']:has-text('Next'), "
                "div[role='button']:has-text('Tiếp')"
            ).first
            next_btn.click(timeout=5000)
            time.sleep(3)
            logger.info("Clicked Next")
        except Exception:
            pass

        # 4. Fill description
        caption = f"{title}\n{description}" if description else title
        logger.info("Setting caption...")
        try:
            desc_editor = page.locator(
                "div[role='textbox'][contenteditable='true'], "
                "textarea[aria-label*='description'], "
                "textarea[aria-label*='mô tả']"
            ).first
            desc_editor.click()
            desc_editor.fill(caption[:2200])
            logger.info("Caption set")
        except Exception as e:
            logger.warning(f"Caption: {e}")

        time.sleep(2)

        # 5. Click Publish/Share Reel
        logger.info("Publishing...")
        time.sleep(3)
        try:
            publish_btn = page.locator(
                "div[role='button']:has-text('Share reel'), "
                "div[role='button']:has-text('Chia sẻ thước phim'), "
                "div[role='button']:has-text('Publish'), "
                "div[role='button']:has-text('Share'), "
                "div[role='button']:has-text('Chia sẻ'), "
                "div[role='button']:has-text('Đăng'), "
                "div[aria-label='Publish'], "
                "div[aria-label='Share']"
            ).first
            publish_btn.click(force=True, timeout=15000)
            logger.info("Clicked Publish")
            time.sleep(8)
        except Exception as e:
            logger.error(f"Publish: {e}")

        return page.url

    def _upload_video_post(self, page, video_path, title, description) -> Optional[str]:
        """Upload as regular Facebook video post"""

        # 1. Go to Facebook
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        # 2. Click "Create post" / "What's on your mind?"
        try:
            create_post = page.locator(
                "div[role='button']:has-text('on your mind'), "
                "div[role='button']:has-text('Bạn đang nghĩ gì')"
            ).first
            create_post.click(timeout=5000)
            time.sleep(3)
            logger.info("Opened post dialog")
        except Exception as e:
            logger.error(f"Create post: {e}")
            raise

        # 3. Click Photo/Video option
        try:
            video_option = page.locator(
                "div[role='button']:has-text('Photo/video'), "
                "div[role='button']:has-text('Ảnh/video')"
            ).first
            video_option.click(timeout=5000)
            time.sleep(2)
        except Exception:
            pass

        # 4. Upload video
        logger.info("Uploading video...")
        try:
            file_input = page.locator("input[type='file'][accept*='video']").first
            file_input.set_input_files(video_path)
            logger.info("Video selected")
        except Exception as e:
            logger.error(f"File input: {e}")
            raise

        time.sleep(5)

        # 5. Fill text
        caption = f"{title}\n{description}" if description else title
        try:
            text_box = page.locator(
                "div[role='textbox'][contenteditable='true']"
            ).first
            text_box.fill(caption)
            logger.info("Caption set")
        except Exception as e:
            logger.warning(f"Caption: {e}")

        time.sleep(2)

        # 6. Post
        logger.info("Posting...")
        try:
            post_btn = page.locator(
                "div[role='button']:has-text('Post'), "
                "div[role='button']:has-text('Đăng')"
            ).first
            post_btn.click(timeout=10000)
            logger.info("Clicked Post")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Post: {e}")

        return page.url
