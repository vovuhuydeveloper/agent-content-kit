"""
Telegram Notifier — Gửi notification + inline approve/reject buttons.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict

import requests

logger = logging.getLogger("agent.notifier")

TELEGRAM_API = "https://api.telegram.org/bot{token}"


class TelegramNotifier:
    """Send Telegram notifications with inline approve/reject buttons"""

    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        self.base_url = TELEGRAM_API.format(token=self.token)

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def notify_video_ready(self, context: Dict[str, Any]) -> bool:
        """
        Send video ready notification with approve/reject inline buttons.

        Returns True if message sent successfully.
        """
        if not self.enabled:
            logger.warning("Telegram not configured — skipping notification")
            return False

        job_id = context.get("job_id", "unknown")
        scripts = context.get("scripts", [])
        videos = context.get("videos", [])
        reviews = context.get("reviews", [])

        # Build message
        title = scripts[0].get("title", "Untitled") if scripts else "Untitled"
        score = reviews[0].get("score", "?") if reviews else "?"
        video_count = len(videos)
        platforms = ", ".join(context.get("platforms", []))
        elapsed = context.get("pipeline_elapsed_seconds", 0)

        # Dashboard URL for viewing video
        base_url = os.environ.get("APP_BASE_URL", "http://localhost:8000")
        job_url = f"{base_url}/jobs/{job_id}"

        message = (
            f"🎬 <b>Video sẵn sàng duyệt!</b>\n\n"
            f"📌 <b>Title:</b> {title}\n"
            f"⭐ <b>AI Score:</b> {score}/10\n"
            f"📹 <b>Videos:</b> {video_count}\n"
            f"📱 <b>Platforms:</b> {platforms}\n"
            f"⏱ <b>Render time:</b> {elapsed:.0f}s\n"
            f"🆔 <code>{job_id}</code>\n\n"
            f"Duyệt để upload lên {platforms}?"
        )

        # Inline keyboard: Approve / Reject
        # Note: Telegram rejects localhost URLs for inline buttons
        buttons = []

        # Only add View button if URL is public (not localhost)
        if job_url and "localhost" not in job_url and "127.0.0.1" not in job_url:
            buttons.append([{"text": "👁 Xem Video", "url": job_url}])

        buttons.append([
            {"text": "✅ Duyệt & Upload", "callback_data": f"approve_{job_id}"},
            {"text": "❌ Từ chối", "callback_data": f"reject_{job_id}"},
        ])

        keyboard = {"inline_keyboard": buttons}

        try:
            # Send text message with buttons
            resp = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "reply_markup": keyboard,
                },
                timeout=10,
            )

            if resp.status_code == 200:
                logger.info(f"📱 Telegram notification sent for job {job_id}")

                # Send video file directly so user can preview in Telegram
                self._send_video(context)

                # Send thumbnail
                self._send_thumbnail(context)
                return True
            else:
                logger.error(f"Telegram send failed: {resp.status_code} {resp.text}")
                return False

        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    def _send_video(self, context: Dict):
        """Send first video file via Telegram"""
        try:
            job_dir = Path(context.get("job_dir", ""))
            videos_dir = job_dir / "videos"

            if not videos_dir.exists():
                return

            # Find first video file
            video_file = None
            for ext in ["*.mp4", "*.webm", "*.mov"]:
                files = list(videos_dir.glob(ext))
                if files:
                    video_file = files[0]
                    break

            if not video_file or not video_file.exists():
                return

            # Telegram limit: 50MB for video
            if video_file.stat().st_size > 50 * 1024 * 1024:
                logger.warning(f"Video too large for Telegram: {video_file.stat().st_size} bytes")
                return

            scripts = context.get("scripts", [])
            title = scripts[0].get("title", "Video") if scripts else "Video"

            with open(video_file, "rb") as f:
                resp = requests.post(
                    f"{self.base_url}/sendVideo",
                    data={
                        "chat_id": self.chat_id,
                        "caption": f"🎬 {title}",
                        "parse_mode": "HTML",
                    },
                    files={"video": f},
                    timeout=60,  # Video upload can be slow
                )
                if resp.status_code == 200:
                    logger.info("📹 Video sent via Telegram")
                else:
                    logger.warning(f"Video send failed: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Video send failed: {e}")

    def _send_thumbnail(self, context: Dict):
        """Send thumbnail image as photo"""
        try:
            job_dir = Path(context.get("job_dir", ""))
            thumb_path = job_dir / "thumbnails" / "thumb_1.jpg"

            if thumb_path.exists():
                with open(thumb_path, "rb") as f:
                    requests.post(
                        f"{self.base_url}/sendPhoto",
                        data={"chat_id": self.chat_id, "caption": "📷 Thumbnail preview"},
                        files={"photo": f},
                        timeout=15,
                    )
        except Exception as e:
            logger.warning(f"Thumbnail send failed: {e}")

    def send_message(self, text: str):
        """Send a simple text message"""
        if not self.enabled:
            return
        try:
            requests.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception:
            pass

    def answer_callback(self, callback_query_id: str, text: str):
        """Answer a callback query (button press)"""
        try:
            requests.post(
                f"{self.base_url}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id, "text": text},
                timeout=5,
            )
        except Exception:
            pass
