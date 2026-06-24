"""
Tests for TelegramNotifier.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.agents.notifier import TelegramNotifier


class TestNotifier:
    """Test TelegramNotifier"""

    @patch.dict("os.environ", {}, clear=True)
    def test_notifier_disabled_when_no_token(self):
        notifier = TelegramNotifier()
        assert notifier.enabled is False

    @patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test-token",
        "TELEGRAM_CHAT_ID": "12345",
    }, clear=True)
    def test_notifier_enabled_with_token(self):
        notifier = TelegramNotifier()
        assert notifier.enabled is True

    @patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test-token",
    }, clear=True)
    def test_notifier_disabled_when_no_chat_id(self):
        notifier = TelegramNotifier()
        assert notifier.enabled is False

    def test_notify_video_ready_skips_when_disabled(self):
        notifier = TelegramNotifier()
        notifier.token = ""
        notifier.chat_id = ""
        result = notifier.notify_video_ready({"job_id": "test-123"})
        assert result is False

    @patch("backend.agents.notifier.requests.post")
    @patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test-bot-token",
        "TELEGRAM_CHAT_ID": "123456789",
    }, clear=True)
    def test_notify_video_ready_sends_message(self, mock_post):
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_post.return_value = mock_success

        notifier = TelegramNotifier()
        context = {
            "job_id": "test-job-001",
            "job_dir": "/tmp/test",
            "scripts": [{"title": "Test Video"}],
            "videos": ["/tmp/video.mp4"],
            "reviews": [{"score": 8}],
            "platforms": ["tiktok", "youtube"],
            "pipeline_elapsed_seconds": 45.2,
        }

        result = notifier.notify_video_ready(context)
        assert result is True
        # Verify sendMessage was called
        assert mock_post.call_count >= 1
        call_kwargs = mock_post.call_args_list[0][1]
        assert "json" in call_kwargs
        assert call_kwargs["json"]["chat_id"] == "123456789"
        assert "Test Video" in call_kwargs["json"]["text"]

    @patch("backend.agents.notifier.requests.post")
    @patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test-bot-token",
        "TELEGRAM_CHAT_ID": "123456789",
    }, clear=True)
    def test_notify_video_ready_handles_api_error(self, mock_post):
        mock_post.return_value.status_code = 400

        notifier = TelegramNotifier()
        result = notifier.notify_video_ready({
            "job_id": "test-job-001",
            "job_dir": "/tmp/test",
            "scripts": [{"title": "Test"}],
            "videos": [],
            "reviews": [],
            "platforms": ["tiktok"],
            "pipeline_elapsed_seconds": 10,
        })

        assert result is False
