"""
Unit tests for KlingClient — HTTP client for Kling AI text-to-video API.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.core.kling_client import KlingClient


class TestKlingClientInit:
    def test_default_constructor(self):
        client = KlingClient()
        assert client.api_key == ""
        assert client.timeout == 300
        assert client.poll_interval == 5.0
        assert client.max_poll_time == 600

    def test_custom_constructor(self):
        client = KlingClient(
            api_key="kl-test-key-12345",
            timeout=120,
            poll_interval=3.0,
            max_poll_time=300,
        )
        assert client.api_key == "kl-test-key-12345"
        assert client.timeout == 120
        assert client.poll_interval == 3.0
        assert client.max_poll_time == 300

    @patch.dict(os.environ, {"KLING_API_KEY": "kl-env-key-67890"}, clear=True)
    def test_from_env_var(self):
        client = KlingClient()
        assert client.api_key == "kl-env-key-67890"

    def test_is_available_with_key(self):
        client = KlingClient(api_key="kl-valid-key-1234567890")
        assert client.is_available() is True

    def test_is_available_without_key(self):
        client = KlingClient(api_key="")
        assert client.is_available() is False

    def test_is_available_short_key(self):
        client = KlingClient(api_key="short")
        assert client.is_available() is False


class TestKlingClientCreateTask:
    @patch("httpx.Client")
    def test_create_task_success(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {"task_id": "task-abc-123"},
        }
        mock_http.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key-12345")
        task_id = client._create_task("a sunset video")

        assert task_id == "task-abc-123"
        # Verify payload
        call_args = mock_http.post.call_args
        payload = call_args[1]["json"]
        assert payload["prompt"] == "a sunset video"
        assert "Authorization" in call_args[1]["headers"]

    @patch("httpx.Client")
    def test_create_task_api_error(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 1, "message": "Invalid prompt"}
        mock_http.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key-12345")
        task_id = client._create_task("bad prompt")
        assert task_id is None

    @patch("httpx.Client")
    def test_create_task_http_error(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_http.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key-12345")
        task_id = client._create_task("test")
        assert task_id is None

    @patch("httpx.Client")
    def test_create_task_includes_optional_fields(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "data": {"task_id": "t1"}}
        mock_http.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key")
        client._create_task(
            "video prompt", duration="10", aspect_ratio="16:9",
            model="kling-v1-6", cfg_scale=0.8,
            negative_prompt="blurry, low quality",
        )
        payload = mock_http.post.call_args[1]["json"]
        assert payload["duration"] == "10"
        assert payload["aspect_ratio"] == "16:9"
        assert payload["model_name"] == "kling-v1-6"
        assert payload["negative_prompt"] == "blurry, low quality"
        assert payload["mode"] == "std"  # v1-6 adds mode


class TestKlingClientPollTask:
    @patch("httpx.Client")
    def test_poll_succeed(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "task_status": "succeed",
                "task_result": {"videos": [{"url": "http://cdn/kling/video.mp4"}]},
            },
        }
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key")
        url = client._poll_task("task-1")
        assert url == "http://cdn/kling/video.mp4"

    @patch("httpx.Client")
    def test_poll_failed(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "task_status": "failed",
                "task_status_msg": "Content policy violation",
            },
        }
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key")
        url = client._poll_task("task-1")
        assert url is None

    @patch("time.sleep", return_value=None)
    @patch("httpx.Client")
    def test_poll_processing_then_succeed(self, mock_client_class, mock_sleep):
        mock_http = MagicMock()
        # First call: processing, second: succeed
        resp_processing = MagicMock()
        resp_processing.status_code = 200
        resp_processing.json.return_value = {
            "code": 0,
            "data": {"task_status": "processing"},
        }
        resp_succeed = MagicMock()
        resp_succeed.status_code = 200
        resp_succeed.json.return_value = {
            "code": 0,
            "data": {
                "task_status": "succeed",
                "task_result": {"videos": [{"url": "http://cdn/v.mp4"}]},
            },
        }
        mock_http.get.side_effect = [resp_processing, resp_succeed]
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key", poll_interval=0.01)
        url = client._poll_task("task-1")
        assert url == "http://cdn/v.mp4"
        assert mock_http.get.call_count == 2

    @patch("time.sleep", return_value=None)
    @patch("httpx.Client")
    def test_poll_timeout(self, mock_client_class, mock_sleep):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {"task_status": "processing"},
        }
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key", poll_interval=0.01, max_poll_time=0)
        url = client._poll_task("task-1")
        assert url is None


class TestKlingClientGenerateVideo:
    @patch.object(KlingClient, "_create_task", return_value="task-xyz")
    @patch.object(KlingClient, "_poll_task", return_value="http://cdn/video.mp4")
    @patch.object(KlingClient, "_download_video", return_value="/out/video.mp4")
    def test_full_flow(self, mock_dl, mock_poll, mock_create, tmp_path):
        client = KlingClient(api_key="kl-key")
        result = client.generate_video(
            "a sunset", output_dir=tmp_path, filename="test.mp4",
        )
        assert result == "/out/video.mp4"
        mock_create.assert_called_once()
        mock_poll.assert_called_once_with("task-xyz")
        mock_dl.assert_called_once()

    def test_no_api_key(self, tmp_path):
        client = KlingClient(api_key="")
        result = client.generate_video("test", output_dir=tmp_path)
        assert result is None

    @patch.object(KlingClient, "_create_task", return_value=None)
    def test_create_fails(self, mock_create, tmp_path):
        client = KlingClient(api_key="kl-key")
        result = client.generate_video("test", output_dir=tmp_path)
        assert result is None

    @patch.object(KlingClient, "_create_task", return_value="task-1")
    @patch.object(KlingClient, "_poll_task", return_value=None)
    def test_poll_fails(self, mock_poll, mock_create, tmp_path):
        client = KlingClient(api_key="kl-key")
        result = client.generate_video("test", output_dir=tmp_path)
        assert result is None


class TestKlingClientDownload:
    @patch("httpx.Client")
    def test_download_success(self, mock_client_class, tmp_path):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake video data"
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key")
        result = client._download_video("http://cdn/v.mp4", tmp_path / "out.mp4")
        assert result == str(tmp_path / "out.mp4")
        assert (tmp_path / "out.mp4").read_bytes() == b"fake video data"

    @patch("httpx.Client")
    def test_download_http_error(self, mock_client_class, tmp_path):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = KlingClient(api_key="kl-key")
        result = client._download_video("http://cdn/missing.mp4", tmp_path / "out.mp4")
        assert result is None
