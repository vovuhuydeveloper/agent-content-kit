"""
AIImageAgent — Generate AI images for each scene.

Provider priority:
  1. Pixelle-Video API (if running) — ComfyUI/FLUX quality
  2. OpenAI DALL-E 3 (if OPENAI_API_KEY set) — works immediately
  3. Skip gracefully → VideoComposer uses Pexels fallback

Enhanced: scene-type-aware prompts (hook vs scene vs CTA),
auto-detection from PIXELLE_VIDEO_API_URL, Pixelle frame rendering.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .base import BaseAgent

logger = logging.getLogger("agent.ai_image")

# ── Scene-type prompt prefixes ──

HOOK_PROMPT_PREFIX = (
    "Trending TikTok viral hook visual, intense neon colors, bold dynamic composition, "
    "dramatic lighting with rim lights, eye-catching high contrast, maximum visual impact, "
    "2025 social media aesthetic, attention-grabbing thumbnail style"
)

SCENE_PROMPT_PREFIX = (
    "Trending TikTok visual style, vibrant saturated colors, dramatic contrast, "
    "neon accent lighting, cinematic depth of field, bold modern aesthetic, "
    "viral social media content style, visually striking composition"
)

CTA_PROMPT_PREFIX = (
    "Call to action visual, engagement-focused, bold eye-catching design, "
    "space for prominent text overlay, subscribe/follow theme, clean central area for words, "
    "viral TikTok ending screen style, bright accent colors, maximum conversion design"
)

# Alternative viral style presets — set VIRAL_STYLE env var to switch
VIRAL_STYLE_PRESETS = {
    "neon": "Neon-lit cyberpunk aesthetic, vibrant pink blue purple lighting, futuristic vibe, bold contrast",
    "cinematic": "Hollywood cinematic lighting, dramatic shadows, golden hour tones, epic composition, film grain",
    "minimal": "Clean minimalist aesthetic, pastel color palette, soft lighting, airy composition, modern luxury feel",
    "dark": "Dark moody aesthetic, chiaroscuro lighting, deep contrasts, mysterious atmosphere, premium feel",
    "vibrant": "Ultra vibrant pop art colors, bold saturated palette, energetic composition, eye-catching maximalist style",
}


class AIImageAgent(BaseAgent):
    name = "AIImageAgent"
    description = "Generate AI images for video scenes (DALL-E / Pixelle-Video)"
    is_critical = False  # Non-critical — pipeline continues with Pexels fallback

    def __init__(self, config=None):
        super().__init__(config)
        self._pixelle_client = None
        self._provider = None  # Will be set in execute()

    def _detect_provider(self) -> str:
        """
        Detect the best available AI image provider.

        Returns: 'pixelle', 'dalle', or 'none'

        Pixelle is auto-detected if:
          - PIXELLE_ENABLED=true, OR
          - PIXELLE_VIDEO_API_URL is configured to a non-default value
        """
        # 1. Try Pixelle-Video
        pixelle_enabled = os.getenv("PIXELLE_ENABLED", "false").lower() in (
            "true", "1", "yes"
        )
        pixelle_url = os.getenv("PIXELLE_VIDEO_API_URL", "")
        # Auto-enable if URL is explicitly set to a non-localhost address
        pixelle_configured = bool(
            pixelle_url
            and pixelle_url != "http://localhost:8085"
            and "://" in pixelle_url
        )

        if pixelle_enabled or pixelle_configured:
            try:
                from ..core.pixelle_client import PixelleClient

                client = PixelleClient()
                if client.is_available():
                    self._pixelle_client = client
                    logger.info(
                        f"🎨 Pixelle-Video connected at {client.api_url}"
                    )
                    return "pixelle"
                elif pixelle_configured:
                    logger.warning(
                        f"Pixelle configured at {pixelle_url} but not reachable"
                    )
            except Exception as e:
                logger.debug(f"Pixelle init failed: {e}")

        # 2. Try OpenAI DALL-E
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key and len(openai_key) > 10:
            return "dalle"

        return "none"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        scripts = context.get("scripts", [])
        job_dir = Path(context["job_dir"])
        language = context.get("language", "vi")

        # Determine image dimensions from aspect_ratio
        aspect_ratio = context.get("aspect_ratio", "9:16")
        img_w, img_h = self._get_image_dimensions(aspect_ratio)

        ai_images_dir = job_dir / "ai_images"
        ai_images_dir.mkdir(exist_ok=True)

        # Detect provider
        self._provider = self._detect_provider()

        if self._provider == "none":
            logger.warning("No AI image provider available — skipping")
            return {
                "ai_images": {},
                "ai_images_available": False,
                "ai_images_count": 0,
            }

        logger.info(f"🎨 Using AI image provider: {self._provider.upper()}")

        all_images: Dict[str, List[Dict]] = {}
        total_generated = 0
        total_failed = 0

        for script in scripts:
            script_id = script.get("script_id", 1)
            scenes = script.get("scenes", [])
            hook = script.get("hook", "")
            cta = script.get("cta", "")
            script_images = []

            # Generate image for hook
            if hook:
                hook_visual = self._extract_visual(
                    {"text": hook, "visual": f"Opening scene: {hook}"},
                    script,
                    language,
                    scene_type="hook",
                )
                img_path = self._generate_image(
                    hook_visual,
                    ai_images_dir,
                    f"s{script_id}_hook.png",
                    img_w,
                    img_h,
                    scene_type="hook",
                )
                if img_path:
                    script_images.append(
                        {
                            "type": "hook",
                            "scene_id": 0,
                            "path": img_path,
                            "prompt": hook_visual,
                        }
                    )
                    total_generated += 1
                else:
                    total_failed += 1

            # Generate images for each scene
            for scene in scenes:
                scene_id = scene.get("scene_id", 1)
                visual_prompt = self._extract_visual(
                    scene, script, language, scene_type="scene"
                )

                img_path = self._generate_image(
                    visual_prompt,
                    ai_images_dir,
                    f"s{script_id}_scene{scene_id}.png",
                    img_w,
                    img_h,
                    scene_type="scene",
                )

                if img_path:
                    script_images.append(
                        {
                            "type": "scene",
                            "scene_id": scene_id,
                            "path": img_path,
                            "prompt": visual_prompt,
                        }
                    )
                    total_generated += 1
                    logger.info(
                        f"🎨 AI image: script {script_id}, scene {scene_id}"
                    )
                else:
                    total_failed += 1
                    logger.warning(
                        f"AI image failed: script {script_id}, scene {scene_id}"
                    )

            # Generate image for CTA
            if cta:
                cta_visual = self._extract_visual(
                    {"text": cta, "visual": f"Call to action: {cta}"},
                    script,
                    language,
                    scene_type="cta",
                )
                img_path = self._generate_image(
                    cta_visual,
                    ai_images_dir,
                    f"s{script_id}_cta.png",
                    img_w,
                    img_h,
                    scene_type="cta",
                )
                if img_path:
                    script_images.append(
                        {
                            "type": "cta",
                            "scene_id": 999,
                            "path": img_path,
                            "prompt": cta_visual,
                        }
                    )
                    total_generated += 1
                else:
                    total_failed += 1

            all_images[str(script_id)] = script_images

        logger.info(
            f"🎨 AI image generation complete ({self._provider}): "
            f"{total_generated} generated, {total_failed} failed"
        )

        return {
            "ai_images": all_images,
            "ai_images_available": total_generated > 0,
            "ai_images_count": total_generated,
            "ai_images_dir": str(ai_images_dir),
            "ai_images_provider": self._provider,
        }

    # ── Image Generation Providers ──

    def _generate_image(
        self,
        prompt: str,
        output_dir: Path,
        filename: str,
        width: int,
        height: int,
        scene_type: str = "scene",
    ) -> Optional[str]:
        """Route to the active provider"""
        if self._provider == "pixelle":
            return self._generate_pixelle(
                prompt, output_dir, filename, width, height, scene_type
            )
        elif self._provider == "dalle":
            return self._generate_dalle(
                prompt, output_dir, filename, width, height, scene_type
            )
        return None

    def _get_prompt_prefix(self, scene_type: str) -> str:
        """
        Get the style prefix for a scene type.

        Override via env vars:
          PIXELLE_IMAGE_PROMPT_PREFIX — custom prefix for ALL scenes
          VIRAL_STYLE — switch between presets: neon, cinematic, minimal, dark, vibrant
        """
        custom_prefix = os.getenv("PIXELLE_IMAGE_PROMPT_PREFIX", "")
        if custom_prefix:
            return custom_prefix

        # Check for viral style preset override
        viral_style = os.getenv("VIRAL_STYLE", "").lower()
        if viral_style in VIRAL_STYLE_PRESETS:
            base_style = VIRAL_STYLE_PRESETS[viral_style]
            if scene_type == "hook":
                return f"{base_style}, attention-grabbing hook, maximum visual impact"
            elif scene_type == "cta":
                return f"{base_style}, call to action, space for text, engagement design"
            else:
                return base_style

        prefixes = {
            "hook": HOOK_PROMPT_PREFIX,
            "scene": SCENE_PROMPT_PREFIX,
            "cta": CTA_PROMPT_PREFIX,
        }
        return prefixes.get(scene_type, SCENE_PROMPT_PREFIX)

    def _generate_dalle(
        self,
        prompt: str,
        output_dir: Path,
        filename: str,
        width: int,
        height: int,
        scene_type: str = "scene",
    ) -> Optional[str]:
        """
        Generate image using OpenAI DALL-E 3.
        Uses the OPENAI_API_KEY already configured for LLM.
        """
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return None

        output_path = Path(output_dir) / filename

        # DALL-E 3 supported sizes: 1024x1024, 1024x1792, 1792x1024
        dalle_size = self._get_dalle_size(width, height)

        # Build prompt with scene-type-aware prefix
        style_prefix = self._get_prompt_prefix(scene_type)
        full_prompt = f"{style_prefix}. {prompt}"

        # Limit prompt length for DALL-E
        if len(full_prompt) > 4000:
            full_prompt = full_prompt[:4000]

        try:
            logger.info(f"🎨 DALL-E generating ({scene_type}): {prompt[:60]}...")

            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": full_prompt,
                    "n": 1,
                    "size": dalle_size,
                    "quality": "standard",
                },
                timeout=90,
            )

            if resp.status_code == 200:
                data = resp.json()
                image_url = data["data"][0]["url"]

                # Download the image
                img_resp = requests.get(image_url, timeout=60)
                if img_resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(img_resp.content)
                    logger.info(
                        f"🎨 DALL-E image saved: {filename} "
                        f"({len(img_resp.content)//1024}KB)"
                    )
                    return str(output_path)

            else:
                error_msg = (
                    resp.json().get("error", {}).get("message", resp.text[:200])
                )
                logger.warning(
                    f"DALL-E error ({resp.status_code}): {error_msg}"
                )

                # If rate limited, wait and skip remaining
                if resp.status_code == 429:
                    logger.warning("DALL-E rate limited — slowing down")
                    time.sleep(5)

        except Exception as e:
            logger.warning(f"DALL-E generation error: {e}")

        return None

    def _generate_pixelle(
        self,
        prompt: str,
        output_dir: Path,
        filename: str,
        width: int,
        height: int,
        scene_type: str = "scene",
    ) -> Optional[str]:
        """
        Generate image via Pixelle-Video API with scene-type-aware prefix.
        """
        if not self._pixelle_client:
            return None

        # Apply scene-type-specific prefix
        prefix = self._get_prompt_prefix(scene_type)
        full_prompt = f"{prefix}, {prompt}"

        return self._pixelle_client.generate_image(
            prompt=full_prompt,
            output_dir=output_dir,
            filename=filename,
            width=width,
            height=height,
        )

    # ── Helpers ──

    def _extract_visual(
        self,
        scene: Dict,
        script: Dict,
        language: str,
        scene_type: str = "scene",
    ) -> str:
        """
        Extract or construct a visual prompt for the scene.

        Enhanced: adjusts prompt style based on scene_type
        (hook = more dynamic, cta = engagement-focused).
        """
        visual = scene.get("visual", "")
        text = scene.get("text", "")
        title = script.get("title", "")
        mood = script.get("mood", "cinematic")

        if visual and len(visual) > 10:
            # Enhance existing visual with scene-type context
            if scene_type == "hook":
                return f"Viral hook visual: {visual}"
            elif scene_type == "cta":
                return f"Engagement prompt: {visual}"
            return visual

        # Build from scene text
        prompt = f"{mood} visual for: {text}"
        if title:
            prompt = f"{prompt}, related to '{title}'"

        return prompt

    def _get_image_dimensions(self, aspect_ratio: str) -> tuple:
        """Get image dimensions based on video aspect ratio"""
        if aspect_ratio == "16:9":
            return 1920, 1080
        elif aspect_ratio == "1:1":
            return 1024, 1024
        else:  # 9:16 default
            return 1080, 1920

    def _get_dalle_size(self, width: int, height: int) -> str:
        """Map video dimensions to DALL-E 3 supported sizes"""
        ratio = width / height
        if ratio > 1.2:
            return "1792x1024"  # landscape
        elif ratio < 0.8:
            return "1024x1792"  # portrait (TikTok/Shorts)
        else:
            return "1024x1024"  # square
