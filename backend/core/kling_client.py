"""
KlingClient — HTTP client for Kling AI text-to-video API.

Kling AI generates short video clips from text prompts.
Perfect for TikTok/Shorts scene backgrounds.

API: https://api.klingai.com
Docs: https://docs.klingai.com
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("core.kling_client")

# Kling AI API base
KLING_API_BASE = "https://api.klingai.com"


class KlingClient:
    """
    HTTP client for Kling AI text-to-video generation.

    Flow:
      1. POST /v1/videos/text2video → task_id
      2. Poll GET /v1/videos/text2video/{task_id} → status
      3. Download video_url when completed

    Usage:
        client = KlingClient(api_key="...")
        video_path = client.generate_video("a futuristic city", output_dir)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 300,
        poll_interval: float = 5.0,
        max_poll_time: int = 600,
    ):
        self.api_key = api_key or os.getenv("KLING_API_KEY", "")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_poll_time = max_poll_time

    def is_available(self) -> bool:
        """Check if Kling API key is configured"""
        return bool(self.api_key and len(self.api_key) > 10)

    def generate_video(
        self,
        prompt: str,
        output_dir: Path,
        filename: str = "",
        duration: str = "5",
        aspect_ratio: str = "9:16",
        model: str = "kling-v1",
        cfg_scale: float = 0.5,
        negative_prompt: str = "",
    ) -> Optional[str]:
        """
        Generate a video clip via Kling AI.

        Args:
            prompt: Text description of the video
            output_dir: Directory to save the generated video
            filename: Output filename (auto-generated if empty)
            duration: Video duration — "5" or "10" (seconds)
            aspect_ratio: "16:9", "9:16", "1:1"
            model: Model name — "kling-v1", "kling-v1-5", "kling-v1-6"
            cfg_scale: Prompt adherence (0.0-1.0)
            negative_prompt: What to avoid

        Returns:
            Path to generated video file, or None on failure
        """
        if not self.api_key:
            logger.warning("Kling API key not configured")
            return None

        if not filename:
            safe_id = abs(hash(prompt)) % 100000
            filename = f"kling_{safe_id:05d}.mp4"

        output_path = Path(output_dir) / filename
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Create generation task
        task_id = self._create_task(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            model=model,
            cfg_scale=cfg_scale,
            negative_prompt=negative_prompt,
        )

        if not task_id:
            return None

        # Step 2: Poll until complete
        video_url = self._poll_task(task_id)

        if not video_url:
            return None

        # Step 3: Download video
        return self._download_video(video_url, output_path)

    def _create_task(
        self,
        prompt: str,
        duration: str = "5",
        aspect_ratio: str = "9:16",
        model: str = "kling-v1",
        cfg_scale: float = 0.5,
        negative_prompt: str = "",
    ) -> Optional[str]:
        """Create a text-to-video generation task"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model_name": model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "cfg_scale": cfg_scale,
        }

        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if model.startswith("kling-v1-6"):
            payload["mode"] = "std"

        try:
            logger.info(f"🎬 Kling creating task: {prompt[:60]}...")
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{KLING_API_BASE}/v1/videos/text2video",
                    headers=headers,
                    json=payload,
                )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    task_id = data["data"]["task_id"]
                    logger.info(f"Kling task created: {task_id}")
                    return task_id

            logger.warning(
                f"Kling create task failed ({resp.status_code}): {resp.text[:300]}"
            )

        except Exception as e:
            logger.warning(f"Kling create task error: {e}")

        return None

    def _poll_task(self, task_id: str) -> Optional[str]:
        """Poll task status until completed or max time reached"""
        headers = {"Authorization": f"Bearer {self.api_key}"}

        start_time = time.time()

        while time.time() - start_time < self.max_poll_time:
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(
                        f"{KLING_API_BASE}/v1/videos/text2video/{task_id}",
                        headers=headers,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 0:
                        task_data = data["data"]
                        status = task_data.get("task_status", "")

                        if status == "succeed":
                            # Get the first video result
                            task_result = task_data.get("task_result", {})
                            videos = task_result.get("videos", [])
                            if videos:
                                video_url = videos[0].get("url", "")
                                if video_url:
                                    logger.info(f"Kling task completed: {task_id}")
                                    return video_url

                            logger.warning(f"Kling task succeeded but no video URL: {task_data}")
                            return None

                        elif status == "failed":
                            fail_msg = task_data.get("task_status_msg", "unknown")
                            logger.warning(f"Kling task failed: {fail_msg}")
                            return None

                        # Still processing — status = "submitted" or "processing"
                        logger.debug(
                            f"Kling task {task_id}: {status} "
                            f"({time.time() - start_time:.0f}s)"
                        )

                    else:
                        logger.warning(f"Kling poll error: {data}")
                        return None

                elif resp.status_code == 429:
                    logger.warning("Kling rate limited — waiting longer...")
                    time.sleep(self.poll_interval * 2)
                    continue
                else:
                    logger.warning(f"Kling poll HTTP {resp.status_code}")
                    return None

            except Exception as e:
                logger.warning(f"Kling poll error: {e}")

            time.sleep(self.poll_interval)

        logger.warning(f"Kling task {task_id} timed out after {self.max_poll_time}s")
        return None

    def _download_video(self, url: str, output_path: Path) -> Optional[str]:
        """Download generated video from URL"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading Kling video...")
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    size_kb = len(resp.content) // 1024
                    logger.info(f"Kling video saved: {output_path.name} ({size_kb}KB)")
                    return str(output_path)

            logger.warning(f"Kling download failed ({resp.status_code})")

        except Exception as e:
            logger.warning(f"Kling download error: {e}")

        return None
