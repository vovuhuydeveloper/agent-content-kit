"""
AIVideoAgent — Generate AI video clips for each scene.

Provider priority:
  1. Kling AI (if KLING_API_KEY set) — text-to-video, 5-10s clips
  2. RunwayML Gen-3/4 (if RUNWAY_API_KEY + RUNWAY_API_SECRET set)
  3. Skip gracefully → AIImageAgent (still images) → Pexels stock → gradient

Scene-type-aware prompts for hook/scene/CTA.
Non-critical agent — pipeline continues with fallbacks on failure.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent

logger = logging.getLogger("agent.ai_video")

# ── Scene-type prompt prefixes for video generation ──

VIDEO_HOOK_PREFIX = (
    "Cinematic opening shot, dramatic motion, intense visual energy, "
    "dynamic camera movement, TikTok viral hook style, high impact first 3 seconds"
)

VIDEO_SCENE_PREFIX = (
    "Smooth cinematic motion, professional camera movement, vibrant colors, "
    "TikTok trend visual style, subtle parallax effect, natural lighting"
)

VIDEO_CTA_PREFIX = (
    "Engaging end screen animation, call to action moment, dynamic zoom, "
    "clean space for text overlay, social media engagement visual, "
    "viral ending style, bright accent lighting"
)


class AIVideoAgent(BaseAgent):
    name = "AIVideoAgent"
    description = "Generate AI video clips for scenes (Kling / Runway)"
    is_critical = False  # Non-critical — pipeline continues with image/stock fallback

    def __init__(self, config=None):
        super().__init__(config)
        self._kling_client = None
        self._runway_client = None
        self._provider = None

    def _detect_provider(self) -> str:
        """
        Detect the best available AI video provider.

        Returns: 'kling', 'runway', or 'none'
        """
        # 1. Try Kling AI
        kling_key = os.getenv("KLING_API_KEY", "")
        if kling_key and len(kling_key) > 10:
            from ..core.kling_client import KlingClient

            self._kling_client = KlingClient(api_key=kling_key)
            logger.info("🎬 Kling AI video provider detected")
            return "kling"

        # 2. Try RunwayML
        runway_key = os.getenv("RUNWAY_API_KEY", "")
        runway_secret = os.getenv("RUNWAY_API_SECRET", "")
        if runway_key and runway_secret and len(runway_key) > 10:
            from ..core.runway_client import RunwayClient

            self._runway_client = RunwayClient(
                api_key=runway_key, api_secret=runway_secret,
            )
            if self._runway_client.is_available():
                logger.info("🎬 RunwayML video provider detected")
                return "runway"

        return "none"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        scripts = context.get("scripts", [])
        job_dir = Path(context["job_dir"])
        aspect_ratio = context.get("aspect_ratio", "9:16")

        ai_videos_dir = job_dir / "ai_videos"
        ai_videos_dir.mkdir(exist_ok=True)

        # Detect provider
        self._provider = self._detect_provider()

        if self._provider == "none":
            logger.warning("No AI video provider available — skipping")
            return {
                "ai_videos": {},
                "ai_videos_available": False,
                "ai_videos_count": 0,
            }

        logger.info(f"🎬 Using AI video provider: {self._provider.upper()}")

        all_videos: Dict[str, List[Dict]] = {}
        total_generated = 0
        total_failed = 0

        for script in scripts:
            script_id = script.get("script_id", 1)
            scenes = script.get("scenes", [])
            hook = script.get("hook", "")
            cta = script.get("cta", "")
            script_videos = []

            # Generate hook video (only first script)
            if hook and script_id == 1:
                hook_prompt = self._build_video_prompt(
                    hook, script, scene_type="hook"
                )
                video_path = self._generate_clip(
                    hook_prompt, ai_videos_dir,
                    f"s{script_id}_hook.mp4", aspect_ratio,
                    scene_type="hook",
                )
                if video_path:
                    script_videos.append({
                        "type": "hook", "scene_id": 0,
                        "path": video_path, "prompt": hook_prompt,
                    })
                    total_generated += 1
                else:
                    total_failed += 1

            # Generate scene videos
            for scene in scenes:
                scene_id = scene.get("scene_id", 1)
                scene_prompt = self._build_video_prompt(
                    scene.get("text", ""), script,
                    visual_hint=scene.get("visual", ""),
                    scene_type="scene",
                )

                video_path = self._generate_clip(
                    scene_prompt, ai_videos_dir,
                    f"s{script_id}_scene{scene_id}.mp4", aspect_ratio,
                    scene_type="scene",
                )

                if video_path:
                    script_videos.append({
                        "type": "scene", "scene_id": scene_id,
                        "path": video_path, "prompt": scene_prompt,
                    })
                    total_generated += 1
                    logger.info(
                        f"🎬 AI video: script {script_id}, scene {scene_id}"
                    )
                else:
                    total_failed += 1
                    logger.warning(
                        f"AI video failed: script {script_id}, scene {scene_id}"
                    )

            # Generate CTA video (only last script)
            if cta and script_id == scripts[-1].get("script_id", script_id):
                cta_prompt = self._build_video_prompt(
                    cta, script, scene_type="cta"
                )
                video_path = self._generate_clip(
                    cta_prompt, ai_videos_dir,
                    f"s{script_id}_cta.mp4", aspect_ratio,
                    scene_type="cta",
                )
                if video_path:
                    script_videos.append({
                        "type": "cta", "scene_id": 999,
                        "path": video_path, "prompt": cta_prompt,
                    })
                    total_generated += 1
                else:
                    total_failed += 1

            all_videos[str(script_id)] = script_videos

        logger.info(
            f"🎬 AI video generation complete ({self._provider}): "
            f"{total_generated} generated, {total_failed} failed"
        )

        return {
            "ai_videos": all_videos,
            "ai_videos_available": total_generated > 0,
            "ai_videos_count": total_generated,
            "ai_videos_dir": str(ai_videos_dir),
            "ai_videos_provider": self._provider,
        }

    def _generate_clip(
        self,
        prompt: str,
        output_dir: Path,
        filename: str,
        aspect_ratio: str,
        scene_type: str = "scene",
    ) -> Optional[str]:
        """Route to the active provider"""
        if self._provider == "kling" and self._kling_client:
            # Determine duration based on scene type
            duration = "5"
            if scene_type == "hook":
                duration = "5"  # Short, punchy
            elif scene_type == "cta":
                duration = "5"
            # Scene duration is 5s — composer will loop/trim as needed

            return self._kling_client.generate_video(
                prompt=prompt,
                output_dir=output_dir,
                filename=filename,
                duration=duration,
                aspect_ratio=aspect_ratio,
                model=os.getenv("KLING_MODEL", "kling-v1"),
            )

        elif self._provider == "runway" and self._runway_client:
            duration = 5
            return self._runway_client.generate_video(
                prompt=prompt,
                output_dir=output_dir,
                filename=filename,
                duration=duration,
                aspect_ratio=aspect_ratio,
                model=os.getenv("RUNWAY_MODEL", "gen3"),
            )

        return None

    def _build_video_prompt(
        self,
        text: str,
        script: Dict,
        visual_hint: str = "",
        scene_type: str = "scene",
    ) -> str:
        """
        Build an optimized video generation prompt.

        Prioritizes explicit visual hints; falls back to scene text + mood.
        Applies scene-type-specific prefix.
        """
        prefix_map = {
            "hook": VIDEO_HOOK_PREFIX,
            "scene": VIDEO_SCENE_PREFIX,
            "cta": VIDEO_CTA_PREFIX,
        }
        prefix = prefix_map.get(scene_type, VIDEO_SCENE_PREFIX)

        # Custom prefix override via env
        custom_prefix = os.getenv("AI_VIDEO_PROMPT_PREFIX", "")
        if custom_prefix:
            prefix = custom_prefix

        # Use visual hint if available
        if visual_hint and len(visual_hint) > 10:
            base = visual_hint
        else:
            mood = script.get("mood", "cinematic")
            title = script.get("title", "")
            base = f"{mood} scene: {text}"
            if title and scene_type == "scene":
                base += f" — context: {title}"

        # Truncate to reasonable prompt length
        full_prompt = f"{prefix}. {base}"
        if len(full_prompt) > 1500:
            full_prompt = full_prompt[:1500]

        return full_prompt
