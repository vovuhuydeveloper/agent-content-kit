"""
RunwayClient — HTTP client for RunwayML Gen-3/Gen-4 video generation API.

RunwayML generates high-quality short video clips from text prompts.
Ideal for professional TikTok/Shorts scene backgrounds.

API: https://api.runwayml.com
Docs: https://docs.runwayml.com
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("core.runway_client")

# RunwayML API base
RUNWAY_API_BASE = "https://api.runwayml.com"


class RunwayClient:
    """
    HTTP client for RunwayML text-to-video generation.

    Flow:
      1. POST /v1/video/generations → generation_id
      2. Poll GET /v1/video/generations/{id} → status
      3. Download video_url when completed

    Usage:
        client = RunwayClient(api_key="...", api_secret="...")
        video_path = client.generate_video("a sunset over mountains", output_dir)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        timeout: int = 300,
        poll_interval: float = 5.0,
        max_poll_time: int = 900,
    ):
        self.api_key = api_key or os.getenv("RUNWAY_API_KEY", "")
        self.api_secret = api_secret or os.getenv("RUNWAY_API_SECRET", "")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_poll_time = max_poll_time

    def is_available(self) -> bool:
        """Check if Runway API credentials are configured"""
        return bool(
            self.api_key and len(self.api_key) > 10
            and self.api_secret and len(self.api_secret) > 10
        )

    def generate_video(
        self,
        prompt: str,
        output_dir: Path,
        filename: str = "",
        duration: int = 5,
        aspect_ratio: str = "9:16",
        model: str = "gen3",
        negative_prompt: str = "",
    ) -> Optional[str]:
        """
        Generate a video clip via RunwayML.

        Args:
            prompt: Text description of the video
            output_dir: Directory to save the generated video
            filename: Output filename (auto-generated if empty)
            duration: Video duration — 5 or 10 seconds
            aspect_ratio: "16:9", "9:16"
            model: "gen3" (Gen-3 Alpha) or "gen4" (Gen-4)
            negative_prompt: What to avoid

        Returns:
            Path to generated video file, or None on failure
        """
        if not self.is_available():
            logger.warning("Runway API credentials not configured")
            return None

        if not filename:
            safe_id = abs(hash(prompt)) % 100000
            filename = f"runway_{safe_id:05d}.mp4"

        output_path = Path(output_dir) / filename
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Create generation
        generation_id = self._create_generation(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            model=model,
            negative_prompt=negative_prompt,
        )

        if not generation_id:
            return None

        # Step 2: Poll until complete
        video_url = self._poll_generation(generation_id)

        if not video_url:
            return None

        # Step 3: Download video
        return self._download_video(video_url, output_path)

    def _create_generation(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        model: str = "gen3",
        negative_prompt: str = "",
    ) -> Optional[str]:
        """Create a generation task"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Runway-Secret": self.api_secret,
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }

        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        try:
            logger.info(f"🎬 Runway creating generation: {prompt[:60]}...")
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{RUNWAY_API_BASE}/v1/video/generations",
                    headers=headers,
                    json=payload,
                )

            if resp.status_code in (200, 201, 202):
                data = resp.json()
                generation_id = data.get("id") or data.get("generation_id")
                if generation_id:
                    logger.info(f"Runway generation created: {generation_id}")
                    return generation_id

            logger.warning(
                f"Runway create failed ({resp.status_code}): {resp.text[:300]}"
            )

        except Exception as e:
            logger.warning(f"Runway create error: {e}")

        return None

    def _poll_generation(self, generation_id: str) -> Optional[str]:
        """Poll generation status until completed"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Runway-Secret": self.api_secret,
        }

        start_time = time.time()

        while time.time() - start_time < self.max_poll_time:
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(
                        f"{RUNWAY_API_BASE}/v1/video/generations/{generation_id}",
                        headers=headers,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "").lower()

                    if status in ("completed", "succeeded", "done"):
                        video_url = (
                            data.get("video_url")
                            or data.get("output_url")
                            or data.get("result", {}).get("url", "")
                        )
                        if video_url:
                            logger.info(f"Runway generation completed: {generation_id}")
                            return video_url

                        logger.warning("Runway completed but no video URL")
                        return None

                    elif status in ("failed", "error", "cancelled"):
                        fail_msg = data.get("error", data.get("message", "unknown"))
                        logger.warning(f"Runway generation failed: {fail_msg}")
                        return None

                    # Still processing
                    elapsed = time.time() - start_time
                    progress = data.get("progress", 0)
                    logger.debug(
                        f"Runway {generation_id}: {status} "
                        f"({progress}%) ({elapsed:.0f}s)"
                    )

                elif resp.status_code == 429:
                    logger.warning("Runway rate limited — waiting longer...")
                    time.sleep(self.poll_interval * 3)
                    continue
                else:
                    logger.warning(f"Runway poll HTTP {resp.status_code}: {resp.text[:200]}")
                    return None

            except Exception as e:
                logger.warning(f"Runway poll error: {e}")

            time.sleep(self.poll_interval)

        logger.warning(
            f"Runway generation {generation_id} timed out after {self.max_poll_time}s"
        )
        return None

    def _download_video(self, url: str, output_path: Path) -> Optional[str]:
        """Download generated video from URL"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info("Downloading Runway video...")
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    size_kb = len(resp.content) // 1024
                    logger.info(
                        f"Runway video saved: {output_path.name} ({size_kb}KB)"
                    )
                    return str(output_path)

            logger.warning(f"Runway download failed ({resp.status_code})")

        except Exception as e:
            logger.warning(f"Runway download error: {e}")

        return None
