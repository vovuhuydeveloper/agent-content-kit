"""
Telegram Bot — Long-polling bot that handles approve/reject callbacks.
Runs as a separate process alongside the worker.
"""

import logging
import os
import threading
import time

import requests

logger = logging.getLogger("telegram_bot")


class TelegramBotHandler:
    """Handle Telegram callback queries for video approval"""

    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0
        self.running = False

    def start_polling(self):
        """Start long-polling in a background thread"""
        if not self.token:
            logger.warning("No TELEGRAM_BOT_TOKEN — bot disabled")
            return

        self.running = True
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()
        logger.info("🤖 Telegram bot started polling")

    def stop(self):
        self.running = False

    def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                resp = requests.get(
                    f"{self.base_url}/getUpdates",
                    params={"offset": self.offset, "timeout": 30},
                    timeout=35,
                )
                if resp.status_code != 200:
                    time.sleep(5)
                    continue

                updates = resp.json().get("result", [])
                for update in updates:
                    self.offset = update["update_id"] + 1
                    self._handle_update(update)

            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)

    def _handle_update(self, update: dict):
        """Handle a single update"""
        # Callback query (button press)
        callback = update.get("callback_query")
        if callback:
            data = callback.get("data", "")
            callback_id = callback["id"]
            user = callback.get("from", {})
            username = user.get("first_name", "Unknown")
            message = callback.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            message_id = message.get("message_id")

            if data.startswith("approve_"):
                job_id = data.replace("approve_", "")
                self._handle_approve(job_id, callback_id, username, chat_id, message_id)
            elif data.startswith("reject_"):
                job_id = data.replace("reject_", "")
                self._handle_reject(job_id, callback_id, username, chat_id, message_id)
            return

        # Text message
        msg = update.get("message", {})
        text = msg.get("text", "")
        chat_id = msg.get("chat", {}).get("id")

        if text == "/start":
            self._send(chat_id, "Content Bot is ready!\nI'll send videos for your approval.")
        elif text == "/status":
            self._send(chat_id, self._get_status_summary())
        elif text == "/help":
            self._send(chat_id, (
                "<b>Content Bot</b>\n\n"
                "/status — View pending jobs\n"
                "/help — Show this menu\n\n"
                "When new videos are ready, I'll send a notification with approve/reject buttons."
            ))

    def _handle_approve(self, job_id: str, callback_id: str, username: str,
                        chat_id: int, message_id: int):
        """Handle approve button"""
        logger.info(f"✅ Job {job_id} APPROVED by {username}")

        # Answer callback
        self._answer_callback(callback_id, "✅ Đã duyệt! Đang upload...")

        # Update message to show approved
        self._edit_message(chat_id, message_id,
                          f"✅ <b>ĐÃ DUYỆT</b> bởi {username}\n🆔 <code>{job_id}</code>\n⏳ Đang upload...")

        # Update DB + trigger publishing
        try:
            from backend.core.database import SessionLocal
            from backend.models.content_job import ContentJob

            db = SessionLocal()
            job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
            if job:
                job.status = "approved"
                db.commit()

                # Trigger publisher in background thread (no Redis needed)
                threading.Thread(
                    target=self._run_publisher_direct,
                    args=(job_id, chat_id),
                    daemon=True,
                ).start()
            else:
                self._send(chat_id, f"❌ Job {job_id} không tìm thấy")
            db.close()
        except Exception as e:
            logger.error(f"Approve handling failed: {e}")
            self._send(chat_id, f"❌ Lỗi: {e}")

    def _handle_reject(self, job_id: str, callback_id: str, username: str,
                       chat_id: int, message_id: int):
        """Handle reject button"""
        logger.info(f"❌ Job {job_id} REJECTED by {username}")

        self._answer_callback(callback_id, "❌ Đã từ chối")
        self._edit_message(chat_id, message_id,
                          f"❌ <b>ĐÃ TỪ CHỐI</b> bởi {username}\n🆔 <code>{job_id}</code>")

        try:
            from backend.core.database import SessionLocal
            from backend.models.content_job import ContentJob

            db = SessionLocal()
            job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
            if job:
                job.status = "rejected"
                db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Reject handling failed: {e}")

    def _send(self, chat_id: int, text: str):
        requests.post(f"{self.base_url}/sendMessage",
                     json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                     timeout=10)

    def _answer_callback(self, callback_id: str, text: str):
        requests.post(f"{self.base_url}/answerCallbackQuery",
                     json={"callback_query_id": callback_id, "text": text},
                     timeout=5)

    def _edit_message(self, chat_id: int, message_id: int, text: str):
        requests.post(f"{self.base_url}/editMessageText",
                     json={"chat_id": chat_id, "message_id": message_id,
                            "text": text, "parse_mode": "HTML"},
                     timeout=10)

    def _run_publisher_direct(self, job_id: str, chat_id: int):
        """Run PublisherAgent directly in this thread (no Celery/Redis needed)"""
        from datetime import datetime, timezone

        from backend.agents.pipeline import Pipeline
        from backend.core.database import SessionLocal
        from backend.models.content_job import ContentJob

        db = SessionLocal()
        try:
            job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
            if not job:
                self._send(chat_id, f"❌ Job {job_id} không tìm thấy")
                return

            job.status = "publishing"
            db.commit()

            # Resume pipeline from PublisherAgent
            pipeline = Pipeline.default()
            job_input = {
                "source_url": job.source_url,
                "language": job.language,
                "video_count": job.video_count,
                "platforms": job.platforms or ["tiktok"],
                "niche": job.niche or "",
                "competitor_urls": job.competitor_urls or [],
                "character_images": job.character_images or [],
                "job_id": job_id,
            }

            result = pipeline.run(job_input, resume_from="PublisherAgent")

            # Update job
            job.status = result.get("pipeline_status", "completed")
            job.published_count = result.get("published_count", 0)
            job.completed_at = datetime.now(timezone.utc)

            # Merge pipeline result
            existing_result = job.pipeline_result or {}
            existing_result["publications"] = result.get("publications", [])
            job.pipeline_result = existing_result
            db.commit()

            logger.info(f"✅ Publishing completed for job {job_id}")
            self._send(chat_id,
                       f"✅ <b>Upload hoàn tất!</b>\n"
                       f"🆔 <code>{job_id}</code>\n"
                       f"📹 Published: {result.get('published_count', 0)} videos")

        except Exception as e:
            logger.error(f"❌ Publishing failed for job {job_id}: {e}")
            try:
                db.rollback()
                job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
                if job:
                    job.status = "publish_failed"
                    job.error_message = str(e)[:500]
                    db.commit()
            except Exception:
                db.rollback()
            self._send(chat_id, f"❌ Upload thất bại: {str(e)[:200]}")
        finally:
            db.close()

    def _get_status_summary(self) -> str:
        try:
            from backend.core.database import SessionLocal
            from backend.models.content_job import ContentJob

            db = SessionLocal()
            pending = db.query(ContentJob).filter(
                ContentJob.status == "awaiting_approval"
            ).count()
            total = db.query(ContentJob).count()
            db.close()
            return f"📊 <b>Status</b>\nChờ duyệt: {pending}\nTổng jobs: {total}"
        except Exception:
            return "📊 Không thể lấy status"


# Singleton
_bot: TelegramBotHandler = None

def start_telegram_bot():
    """Start the bot (called from worker startup)"""
    global _bot
    if _bot is None:
        _bot = TelegramBotHandler()
        _bot.start_polling()
    return _bot
