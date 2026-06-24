"""
Unit tests for PixelleClient — HTTP client for Pixelle-Video API.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import httpx
import pytest

from backend.core.pixelle_client import PixelleClient


class TestPixelleClientInit:
    """Test PixelleClient initialization and configuration"""

    def test_default_constructor(self):
        client = PixelleClient()
        assert client.api_url == "http://localhost:8085"
        assert client.timeout == 120
        assert client.max_retries == 2
        assert client._available is None

    def test_custom_constructor(self):
        client = PixelleClient(
            api_url="http://custom:9000",
            timeout=60,
            max_retries=3,
        )
        assert client.api_url == "http://custom:9000"
        assert client.timeout == 60
        assert client.max_retries == 3

    def test_strips_trailing_slash(self):
        client = PixelleClient(api_url="http://example.com/api/")
        assert client.api_url == "http://example.com/api"

    @patch.dict(os.environ, {
        "PIXELLE_VIDEO_API_URL": "http://env-url:9999",
        "PIXELLE_REQUEST_TIMEOUT": "90",
    })
    def test_from_env_vars(self):
        client = PixelleClient()
        assert client.api_url == "http://env-url:9999"
        assert client.timeout == 90


class TestPixelleClientHealthCheck:
    """Test health check and availability detection"""

    @patch.object(PixelleClient, "_client")
    def test_is_available_healthy(self, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http.get.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        assert client.is_available() is True
        # Cached — second call should not trigger HTTP
        assert client.is_available() is True
        mock_http.get.assert_called_once_with("/health", timeout=5.0)

    @patch.object(PixelleClient, "_client")
    def test_is_available_unhealthy(self, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_http.get.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        assert client.is_available() is False

    @patch.object(PixelleClient, "_client")
    def test_is_available_connection_error(self, mock_client_factory):
        mock_http = MagicMock()
        mock_http.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        assert client.is_available() is False

    @patch.object(PixelleClient, "_client")
    def test_health_check_returns_data(self, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "1.0.0"}
        mock_http.get.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        result = client.health_check()
        assert result["status"] == "healthy"
        assert result["data"] == {"version": "1.0.0"}
        assert result["url"] == "http://localhost:8085"

    @patch.object(PixelleClient, "_client")
    def test_health_check_unhealthy_error(self, mock_client_factory):
        mock_http = MagicMock()
        mock_http.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        result = client.health_check()
        assert result["status"] == "unhealthy"
        assert "Timeout" in result["error"]


class TestPixelleClientGenerateImage:
    """Test image generation via Pixelle API"""

    @patch.object(PixelleClient, "_client")
    @patch.object(PixelleClient, "_download_file")
    def test_generate_image_success_with_url(self, mock_download, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"image_url": "http://cdn/images/123.png"}
        mock_http.post.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        mock_download.return_value = "/output/test.png"

        client = PixelleClient()
        result = client.generate_image(
            "a beautiful sunset",
            output_dir=Path("/tmp"),
            filename="test.png",
            width=1024,
            height=1024,
        )
        assert result == "/output/test.png"
        mock_download.assert_called_once_with(
            "http://cdn/images/123.png", Path("/tmp/test.png")
        )

    @patch.object(PixelleClient, "_client")
    def test_generate_image_success_with_path(self, mock_client_factory, tmp_path):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "image_path": str(tmp_path / "generated.png"),
        }
        mock_http.post.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        # Create the file so it "exists"
        (tmp_path / "generated.png").write_text("fake image data")

        client = PixelleClient()
        result = client.generate_image(
            "a sunset",
            output_dir=tmp_path,
        )
        assert result == str(tmp_path / "generated.png")

    @patch.object(PixelleClient, "_client")
    def test_generate_image_missing_url_and_path(self, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "done"}
        mock_http.post.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        result = client.generate_image(
            "a sunset",
            output_dir=Path("/tmp"),
        )
        assert result is None

    @patch.object(PixelleClient, "_client")
    def test_generate_image_http_error(self, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_http.post.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        result = client.generate_image(
            "a sunset",
            output_dir=Path("/tmp"),
        )
        assert result is None

    @patch.object(PixelleClient, "_client")
    def test_generate_image_retry_then_success(self, mock_client_factory):
        mock_http = MagicMock()
        # First attempt: timeout, second: success
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {
            "image_url": "http://cdn/img.png",
        }
        mock_http.post.side_effect = [
            httpx.TimeoutException("timeout"),
            mock_response_ok,
        ]
        mock_client_factory.return_value.__enter__.return_value = mock_http

        with patch.object(PixelleClient, "_download_file", return_value="/out/img.png"):
            client = PixelleClient(max_retries=2)
            result = client.generate_image(
                "a sunset",
                output_dir=Path("/tmp"),
                filename="img.png",
            )
            assert result == "/out/img.png"
            assert mock_http.post.call_count == 2

    @patch.object(PixelleClient, "_client")
    def test_generate_image_all_retries_exhausted(self, mock_client_factory):
        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.TimeoutException("timeout")
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient(max_retries=1)
        result = client.generate_image(
            "a sunset",
            output_dir=Path("/tmp"),
        )
        assert result is None
        assert mock_http.post.call_count == 2  # initial + 1 retry

    @patch.object(PixelleClient, "_client")
    def test_generate_image_applies_prompt_prefix(self, mock_client_factory):
        """Verify prompt prefix is applied in the API payload"""
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"image_url": "http://cdn/x.png"}
        mock_http.post.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        with patch.object(PixelleClient, "_download_file", return_value="/out/x.png"):
            client = PixelleClient()
            client.generate_image(
                "a sunset",
                output_dir=Path("/tmp"),
                prompt_prefix="Cinematic drone shot",
                workflow="custom/wf.json",
            )
            call_args = mock_http.post.call_args
            payload = call_args[1]["json"]
            assert "Cinematic drone shot" in payload["prompt"]
            assert "a sunset" in payload["prompt"]
            assert payload["workflow"] == "custom/wf.json"


class TestPixelleClientTTS:
    """Test TTS generation"""

    @patch.object(PixelleClient, "_client")
    @patch.object(PixelleClient, "_download_file")
    def test_generate_tts_success(self, mock_download, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"audio_url": "http://cdn/audio.mp3"}
        mock_http.post.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        mock_download.return_value = "/out/audio.mp3"

        client = PixelleClient()
        result = client.generate_tts(
            "Hello world",
            output_path=Path("/tmp/audio.mp3"),
        )
        assert result == "/out/audio.mp3"

    @patch.object(PixelleClient, "_client")
    def test_generate_tts_failure(self, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_http.post.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        result = client.generate_tts(
            "",
            output_path=Path("/tmp/audio.mp3"),
        )
        assert result is None


class TestPixelleClientRenderFrame:
    """Test frame rendering"""

    @patch.object(PixelleClient, "_client")
    @patch.object(PixelleClient, "_download_file")
    def test_render_frame_success(self, mock_download, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"frame_url": "http://cdn/frame.png"}
        mock_http.post.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        mock_download.return_value = "/out/frame.png"

        client = PixelleClient()
        result = client.render_frame(
            template="1080x1920/image_default.html",
            title="Test",
            text="Scene text",
            image_path="/img/bg.png",
            output_path=Path("/tmp/frame.png"),
            ext={"watermark": "brand"},
        )
        assert result == "/out/frame.png"

    @patch.object(PixelleClient, "_client")
    def test_render_frame_failure(self, mock_client_factory):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_http.post.return_value = mock_response
        mock_client_factory.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        result = client.render_frame(
            template="default",
            title="Test",
            text="Text",
            image_path="/img/bg.png",
            output_path=Path("/tmp/frame.png"),
        )
        assert result is None


class TestPixelleClientDownloadFile:
    """Test file download utility"""

    @patch("httpx.Client")
    def test_download_file_success(self, mock_client_class, tmp_path):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake image binary data"
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        output = tmp_path / "downloaded.png"
        result = client._download_file("http://cdn/file.png", output)
        assert result == str(output)
        assert output.read_bytes() == b"fake image binary data"

    @patch("httpx.Client")
    def test_download_file_relative_url(self, mock_client_class, tmp_path):
        """Relative URLs should be prefixed with api_url"""
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"data"
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = PixelleClient(api_url="http://pixelle:8085")
        output = tmp_path / "rel.png"
        client._download_file("/files/image.png", output)
        mock_http.get.assert_called_once_with("http://pixelle:8085/files/image.png")

    @patch("httpx.Client")
    def test_download_file_http_error(self, mock_client_class, tmp_path):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        result = client._download_file("http://cdn/missing.png", tmp_path / "out.png")
        assert result is None

    @patch("httpx.Client")
    def test_download_file_creates_parent_dir(self, mock_client_class, tmp_path):
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"data"
        mock_http.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_http

        client = PixelleClient()
        output = tmp_path / "subdir" / "nested" / "file.png"
        client._download_file("http://cdn/file.png", output)
        assert output.exists()
