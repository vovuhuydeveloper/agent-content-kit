"""
YouTubePlaywrightUploader — Upload videos to YouTube Studio via browser automation.
Uses saved session from BrowserSession (no OAuth API needed).
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("uploader.youtube_playwright")


class YouTubePlaywrightUploader:
    """Upload videos to YouTube Studio using Playwright browser automation"""

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list = None,
        thumbnail_path: str = None,
        privacy: str = "PRIVATE",
    ) -> Dict:
        """
        Upload a video to YouTube Studio via browser.

        Returns:
            Dict with status, post_id, post_url
        """
        from playwright.sync_api import sync_playwright

        video_path = str(Path(video_path).resolve())
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        from backend.core.browser_session import BrowserSession

        if not BrowserSession.has_session("youtube"):
            raise RuntimeError(
                "YouTube not connected. Run: "
                "python -m backend.core.browser_session login youtube"
            )

        logger.info(f"Uploading to YouTube: {title}")

        with sync_playwright() as p:
            context = BrowserSession.get_context("youtube", p, headless=False)

            try:
                page = context.pages[0] if context.pages else context.new_page()
                video_url = self._do_upload(
                    page, video_path, title, description, tags, thumbnail_path, privacy
                )

                if video_url:
                    video_id = video_url.split("v=")[-1] if "v=" in video_url else ""
                    logger.info(f"✅ YouTube upload complete: {video_url}")
                    return {
                        "status": "published",
                        "post_id": video_id,
                        "post_url": video_url,
                        "platform": "youtube",
                    }
                else:
                    logger.warning("Upload completed but could not extract URL")
                    return {
                        "status": "published",
                        "post_id": None,
                        "post_url": None,
                        "platform": "youtube",
                        "note": "Uploaded but URL extraction failed. Check YouTube Studio.",
                    }
            except Exception as e:
                logger.error(f"YouTube Playwright upload failed: {e}")
                raise
            finally:
                context.close()

    def _do_upload(
        self, page, video_path, title, description, tags, thumbnail_path, privacy
    ) -> Optional[str]:
        """Execute the upload flow in YouTube Studio"""

        # 1. Navigate to YouTube Studio
        page.goto("https://studio.youtube.com/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)
        logger.info(f"Studio loaded: {page.url}")

        # 2. Click "Create" button
        try:
            create_btn = page.locator(
                "[aria-label='Create'], "
                "ytcp-button#create-icon, "
                "button:has-text('Create'), "
                "button:has-text('Tạo')"
            ).first
            create_btn.click(timeout=8000)
            time.sleep(2)
            logger.info("Clicked Create")
        except Exception as e:
            logger.error(f"Create button not found: {e}")
            raise

        # 3. Click "Upload videos" from dropdown menu
        try:
            upload_item = page.locator(
                "yt-formatted-string:has-text('Upload videos'), "
                "yt-formatted-string:has-text('Tải video lên')"
            ).first
            upload_item.click(force=True, timeout=5000)
            time.sleep(3)
            logger.info("Clicked Upload videos")
        except Exception as e:
            logger.error(f"Upload videos not found: {e}")
            raise

        # 4. Wait for file input and upload video
        logger.info("Uploading video file...")
        try:
            file_input = page.locator("input[type='file']").first
            file_input.wait_for(state="attached", timeout=10000)
            file_input.set_input_files(video_path)
            logger.info("Video file selected")
        except Exception as e:
            logger.error(f"File input not found: {e}")
            raise

        # 5. Wait for upload dialog
        time.sleep(5)

        # 6. Fill title
        logger.info(f"Setting title: {title[:50]}...")
        try:
            title_box = page.locator("#textbox[aria-label]").first
            title_box.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            time.sleep(0.5)
            title_box.fill(title[:100])
            logger.info("Title set")
        except Exception as e:
            logger.warning(f"Title input: {e}")

        time.sleep(1)

        # 7. Fill description
        if description:
            logger.info("Setting description...")
            try:
                desc_box = page.locator("#textbox[aria-label]").nth(1)
                desc_box.click()
                desc_box.fill(description[:5000])
                logger.info("Description set")
            except Exception as e:
                logger.warning(f"Description: {e}")

        time.sleep(1)

        # 8. Upload thumbnail
        if thumbnail_path and Path(thumbnail_path).exists():
            logger.info("Uploading thumbnail...")
            try:
                thumb_inputs = page.locator("input[type='file']").all()
                if len(thumb_inputs) > 1:
                    thumb_inputs[1].set_input_files(str(Path(thumbnail_path).resolve()))
                    logger.info("Thumbnail uploaded")
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"Thumbnail: {e}")

        # 9. Set "Not for kids"
        try:
            not_for_kids = page.locator(
                "tp-yt-paper-radio-button[name='NOT_MADE_FOR_KIDS'], "
                "tp-yt-paper-radio-button:has-text('No, it')"
            ).first
            not_for_kids.click(timeout=3000)
            logger.info("Set: Not for kids")
        except Exception:
            logger.warning("Could not set 'Not for kids'")

        time.sleep(1)

        # 10. Click Next 3 times (Details → Elements → Checks → Visibility)
        for step in range(3):
            try:
                next_btn = page.locator("#next-button").first
                next_btn.click(timeout=5000)
                time.sleep(2)
                logger.info(f"Next step {step + 1}")
            except Exception:
                break

        # 11. Set visibility
        logger.info(f"Setting visibility: {privacy}")
        time.sleep(1)
        try:
            page.locator(
                f"tp-yt-paper-radio-button[name='{privacy}']"
            ).first.click(timeout=3000)
            logger.info(f"Visibility: {privacy}")
        except Exception as e:
            logger.warning(f"Privacy: {e}")

        # 12. Wait for upload processing
        logger.info("Waiting for processing...")
        for i in range(90):
            try:
                done = page.locator("#done-button").first
                if done.is_enabled():
                    break
            except Exception:
                pass
            time.sleep(5)

        time.sleep(2)

        # 13. Click "Done" / "Save"
        logger.info("Publishing...")
        try:
            done_btn = page.locator("#done-button").first
            done_btn.click(timeout=10000)
            logger.info("Clicked Done/Publish")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Done button: {e}")

        # 14. Extract video URL
        video_url = None
        try:
            link = page.locator(
                "a[href*='youtu.be'], "
                "a[href*='youtube.com/watch'], "
                "a[href*='studio.youtube.com/video']"
            ).first
            href = link.get_attribute("href", timeout=8000)
            if href:
                video_url = href if href.startswith("http") else f"https:{href}"
                logger.info(f"Video URL: {video_url}")
        except Exception:
            try:
                url_text = page.locator(
                    "span:has-text('youtu.be'), "
                    "span:has-text('youtube.com/watch')"
                ).first.inner_text(timeout=3000)
                if url_text:
                    video_url = url_text.strip()
                    if not video_url.startswith("http"):
                        video_url = f"https://{video_url}"
            except Exception:
                logger.warning("Could not extract video URL")

        # Close dialog
        try:
            page.locator(
                "ytcp-button:has-text('Close'), "
                "ytcp-button:has-text('Đóng'), "
                "#close-button"
            ).first.click(timeout=3000)
        except Exception:
            pass

        return video_url
