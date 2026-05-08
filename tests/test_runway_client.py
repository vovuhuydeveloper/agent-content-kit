"""
Unit tests for RunwayClient — HTTP client for RunwayML video generation API.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.core.runway_client import RunwayClient


class TestRunwayClientInit:
    def test_default_constructor(self):
        client = RunwayClient()
        assert client.api_key == ""
        assert client.api_secret == ""
        assert client.timeout == 300
        assert client.max_poll_time == 900

    def test_custom_constructor(self):
        client = RunwayClient(
            api_key="rw-key-123", api_secret="rw-secret-456",
            timeout=180, max_poll_time=600,
        )
        assert client.api_key == "rw-key-123"
        assert client.api_secret == "rw-secret-456"

    @patch.dict(os.environ, {
        "RUNWAY_API_KEY": "env-key", "RUNWAY_API_SECRET": "env-secret",
    }, clear=True)
    def test_from_env_vars(self):
        client = RunwayClient()
        assert client.api_key == "env-key"
        assert client.api_secret == "env-secret"

    def test_is_available_with_creds(self):
        client = RunwayClient(api_key="rw-key-1234567890", api_secret="rw-secret-1234567890")
        assert client.is_available() is True

    def test_is_available_without_key(self):
        client = RunwayClient(api_key="", api_secret="secret")
        assert client.is_available() is False

    def test_is_available_without_secret(self):
        client = RunwayClient(api_key="key1234567890", api_secret="")
        assert client.is_available() is False


class TestRunwayClientCreateGeneration:
    @patch("httpx.Client")
    def test_create_success(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "gen-abc-123"}
        mock_http.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = RunwayClient(api_key="key", api_secret="secret")
        gen_id = client._create_generation("a sunset")

        assert gen_id == "gen-abc-123"
        call_args = mock_http.post.call_args
        payload = call_args[1]["json"]
        assert payload["prompt"] == "a sunset"
        assert payload["model"] == "gen3"

    @patch("httpx.Client")
    def test_create_http_error(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_http.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = RunwayClient(api_key="key", api_secret="secret")
        gen_id = client._create_generation("test")
        assert gen_id is None


class TestRunwayClientPollGeneration:
    @patch("httpx.Client")
    def test_poll_completed(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "completed",
            "video_url": "http://cdn/runway/video.mp4",
        }
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = RunwayClient(api_key="key", api_secret="secret")
        url = client._poll_generation("gen-1")
        assert url == "http://cdn/runway/video.mp4"

    @patch("httpx.Client")
    def test_poll_failed(self, mock_client_class):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "failed",
            "error": "Generation failed",
        }
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = RunwayClient(api_key="key", api_secret="secret")
        url = client._poll_generation("gen-1")
        assert url is None

    @patch("time.sleep", return_value=None)
    @patch("httpx.Client")
    def test_poll_processing_then_done(self, mock_client_class, mock_sleep):
        mock_http = MagicMock()
        resp_proc = MagicMock()
        resp_proc.status_code = 200
        resp_proc.json.return_value = {"status": "processing", "progress": 50}
        resp_done = MagicMock()
        resp_done.status_code = 200
        resp_done.json.return_value = {"status": "completed", "video_url": "http://cdn/v.mp4"}
        mock_http.get.side_effect = [resp_proc, resp_done]
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = RunwayClient(api_key="key", api_secret="secret", poll_interval=0.01)
        url = client._poll_generation("gen-1")
        assert url == "http://cdn/v.mp4"


class TestRunwayClientGenerateVideo:
    @patch.object(RunwayClient, "is_available", return_value=True)
    @patch.object(RunwayClient, "_create_generation", return_value="gen-xyz")
    @patch.object(RunwayClient, "_poll_generation", return_value="http://cdn/v.mp4")
    @patch.object(RunwayClient, "_download_video", return_value="/out/v.mp4")
    def test_full_flow(self, mock_dl, mock_poll, mock_create, mock_avail, tmp_path):
        client = RunwayClient(api_key="key", api_secret="secret")
        result = client.generate_video("a sunset", output_dir=tmp_path)
        assert result == "/out/v.mp4"

    def test_no_creds(self, tmp_path):
        client = RunwayClient(api_key="", api_secret="")
        result = client.generate_video("test", output_dir=tmp_path)
        assert result is None

    @patch.object(RunwayClient, "_create_generation", return_value=None)
    def test_create_fails(self, mock_create, tmp_path):
        client = RunwayClient(api_key="key", api_secret="secret")
        result = client.generate_video("test", output_dir=tmp_path)
        assert result is None