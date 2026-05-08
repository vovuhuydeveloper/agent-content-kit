"""
PixelleClient — HTTP client for Pixelle-Video API.
Wraps image generation, video generation, TTS, and frame rendering
with retry logic and graceful fallback.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("core.pixelle_client")


class PixelleClient:
    """
    HTTP client for communicating with Pixelle-Video API service.

    Usage:
        client = PixelleClient()
        if client.is_available():
            image_path = client.generate_image("a sunset over mountains", output_dir, width=1024, height=1024)
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: int = 2,
    ):
        self.api_url = (
            api_url
            or os.getenv("PIXELLE_VIDEO_API_URL", "http://localhost:8085")
        ).rstrip("/")
        self.timeout = timeout or int(os.getenv("PIXELLE_REQUEST_TIMEOUT", "120"))
        self.max_retries = max_retries
        self._available: Optional[bool] = None

    def _client(self) -> httpx.Client:
        """Create a new httpx client for each request (thread-safe)"""
        return httpx.Client(
            base_url=self.api_url,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
        )

    def is_available(self) -> bool:
        """
        Check if Pixelle-Video service is running and healthy.
        Caches result for the lifetime of this client instance.
        """
        if self._available is not None:
            return self._available

        try:
            with self._client() as client:
                resp = client.get("/health", timeout=5.0)
                self._available = resp.status_code == 200
        except Exception as e:
            logger.debug(f"Pixelle-Video health check failed: {e}")
            self._available = False

        if self._available:
            logger.info(f"✅ Pixelle-Video connected at {self.api_url}")
        else:
            logger.warning(f"⚠️ Pixelle-Video unavailable at {self.api_url} — will use fallback")

        return self._available

    def health_check(self) -> Dict[str, Any]:
        """Full health check returning service info"""
        try:
            with self._client() as client:
                resp = client.get("/health", timeout=5.0)
                if resp.status_code == 200:
                    return {"status": "healthy", "data": resp.json(), "url": self.api_url}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "url": self.api_url}
        return {"status": "unhealthy", "url": self.api_url}

    def generate_image(
        self,
        prompt: str,
        output_dir: Path,
        filename: str = "",
        width: int = 1024,
        height: int = 1024,
        workflow: Optional[str] = None,
        prompt_prefix: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate an AI image via Pixelle-Video API.

        Args:
            prompt: Image description/prompt
            output_dir: Directory to save the downloaded image
            filename: Output filename (auto-generated if empty)
            width: Image width
            height: Image height
            workflow: ComfyUI workflow key (uses config default if None)
            prompt_prefix: Style prefix for prompt (uses config default if None)

        Returns:
            Path to generated image file, or None on failure
        """
        if not filename:
            filename = f"ai_img_{int(time.time())}_{hash(prompt) % 10000:04d}.png"

        output_path = Path(output_dir) / filename
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build full prompt with prefix
        if prompt_prefix is None:
            prompt_prefix = os.getenv(
                "PIXELLE_IMAGE_PROMPT_PREFIX",
                "High quality, cinematic style illustration"
            )

        full_prompt = f"{prompt_prefix}, {prompt}" if prompt_prefix else prompt

        if workflow is None:
            workflow = os.getenv("PIXELLE_IMAGE_WORKFLOW", "runninghub/image_flux.json")

        payload = {
            "prompt": full_prompt,
            "width": width,
            "height": height,
            "workflow": workflow,
        }

        for attempt in range(self.max_retries + 1):
            try:
                with self._client() as client:
                    logger.info(f"🎨 Generating AI image (attempt {attempt + 1}): {prompt[:60]}...")
                    resp = client.post("/api/image/generate", json=payload)

                    if resp.status_code == 200:
                        data = resp.json()

                        # Pixelle API returns image URL or base64
                        image_url = data.get("image_url") or data.get("url")
                        if image_url:
                            return self._download_file(image_url, output_path)

                        # Or returns file path on shared volume
                        image_path = data.get("image_path") or data.get("path")
                        if image_path and Path(image_path).exists():
                            return str(image_path)

                        logger.warning(f"Pixelle image response missing URL/path: {data}")
                        return None
                    else:
                        logger.warning(
                            f"Pixelle image generation failed ({resp.status_code}): "
                            f"{resp.text[:200]}"
                        )

            except httpx.TimeoutException:
                logger.warning(f"Pixelle image generation timeout (attempt {attempt + 1})")
            except Exception as e:
                logger.warning(f"Pixelle image generation error (attempt {attempt + 1}): {e}")

            if attempt < self.max_retries:
                time.sleep(2 ** attempt)

        return None

    def generate_tts(
        self,
        text: str,
        output_path: Path,
        workflow: Optional[str] = None,
        ref_audio: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate TTS audio via Pixelle-Video API.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file
            workflow: TTS workflow key
            ref_audio: Reference audio for voice cloning

        Returns:
            Path to generated audio file, or None on failure
        """
        payload = {
            "text": text,
        }
        if workflow:
            payload["workflow"] = workflow
        if ref_audio:
            payload["ref_audio"] = ref_audio

        try:
            with self._client() as client:
                resp = client.post("/api/tts/generate", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    audio_url = data.get("audio_url") or data.get("url")
                    if audio_url:
                        return self._download_file(audio_url, output_path)
                    audio_path = data.get("audio_path") or data.get("path")
                    if audio_path:
                        return str(audio_path)
                else:
                    logger.warning(f"Pixelle TTS failed ({resp.status_code}): {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"Pixelle TTS error: {e}")

        return None

    def render_frame(
        self,
        template: str,
        title: str,
        text: str,
        image_path: str,
        output_path: Path,
        ext: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Render an HTML template frame via Pixelle-Video API.

        Args:
            template: Template name (e.g., "1080x1920/image_default.html")
            title: Video title
            text: Scene narration text
            image_path: Path to scene image
            output_path: Path to save rendered frame

        Returns:
            Path to rendered frame image, or None on failure
        """
        payload = {
            "template": template,
            "title": title,
            "text": text,
            "image": image_path,
        }
        if ext:
            payload["ext"] = ext

        try:
            with self._client() as client:
                resp = client.post("/api/frame/render", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    frame_url = data.get("frame_url") or data.get("url")
                    if frame_url:
                        return self._download_file(frame_url, output_path)
                    frame_path = data.get("frame_path") or data.get("path")
                    if frame_path:
                        return str(frame_path)
                else:
                    logger.warning(f"Pixelle frame render failed ({resp.status_code})")
        except Exception as e:
            logger.warning(f"Pixelle frame render error: {e}")

        return None

    def _download_file(self, url: str, output_path: Path) -> Optional[str]:
        """Download a file from URL to local path"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle relative URLs from Pixelle API
            if url.startswith("/"):
                url = f"{self.api_url}{url}"

            with httpx.Client(timeout=60.0) as dl_client:
                resp = dl_client.get(url)
                if resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    logger.debug(f"Downloaded: {output_path} ({len(resp.content)} bytes)")
                    return str(output_path)
                else:
                    logger.warning(f"Download failed ({resp.status_code}): {url}")
        except Exception as e:
            logger.warning(f"Download error: {e}")
        return None
""" 
Description = "HTTP client for Pixelle-Video API with retry logic, timeout handling, and graceful fallback. Supports image generation, TTS, and HTML frame rendering via REST calls."
IsArtifact = false
"""
