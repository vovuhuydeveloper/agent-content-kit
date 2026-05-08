"""
CharacterAgent — Generate animated talking character overlays.

Modes:
  - "static" (default): Single static character image overlay
  - "talking_pet": Animated pet character with breathing + talking mouth
  - "talking_avatar": Animated avatar with head movement + lip sync

Uses PIL to generate frame sequences from a static character image.
Non-critical agent — pipeline continues with static overlay if animation fails.

Character image requirements:
  - PNG with transparent background
  - Face centered in the image
  - Placed in data/characters/ directory
"""

import logging
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from .base import BaseAgent

logger = logging.getLogger("agent.character")

# Character mode constants
CHARACTER_MODE_STATIC = "static"
CHARACTER_MODE_TALKING_PET = "talking_pet"
CHARACTER_MODE_TALKING_AVATAR = "talking_avatar"

VALID_MODES = {CHARACTER_MODE_STATIC, CHARACTER_MODE_TALKING_PET, CHARACTER_MODE_TALKING_AVATAR}


class CharacterAgent(BaseAgent):
    name = "CharacterAgent"
    description = "Generate animated talking character overlays for video scenes"
    is_critical = False  # Non-critical — pipeline uses static fallback

    def __init__(self, config=None):
        super().__init__(config)
        self._frames_dir = None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        character_mode = context.get("character_mode", CHARACTER_MODE_STATIC)
        character_images = context.get("character_images", [])
        scripts = context.get("scripts", [])
        job_dir = Path(context["job_dir"])

        # Validate mode
        if character_mode not in VALID_MODES:
            logger.warning(
                f"Unknown character_mode '{character_mode}' — "
                f"falling back to '{CHARACTER_MODE_STATIC}'"
            )
            character_mode = CHARACTER_MODE_STATIC

        # Static mode — nothing to do (composer handles static overlay)
        if character_mode == CHARACTER_MODE_STATIC:
            logger.info("Character mode: static (existing overlay)")
            return {
                "character_mode": CHARACTER_MODE_STATIC,
                "character_frames": {},
                "character_frames_available": False,
                "character_fps": 0,
            }

        # Find character image
        char_image = self._find_character_image(character_images)
        if not char_image:
            logger.warning("No character image found — skipping animation")
            return {
                "character_mode": character_mode,
                "character_frames": {},
                "character_frames_available": False,
                "character_fps": 0,
            }

        logger.info(f"🎭 Character mode: {character_mode} — generating animated frames")

        # Setup output directory
        self._frames_dir = job_dir / "character_frames"
        self._frames_dir.mkdir(exist_ok=True)

        # Build segments from scripts (same logic as composer)
        segments = self._build_all_segments(scripts)
        if not segments:
            return {
                "character_mode": character_mode,
                "character_frames": {},
                "character_frames_available": False,
                "character_fps": 0,
            }

        # Generate frame sequences per segment
        fps = 6  # Frames per second for character animation
        all_frames: Dict[str, List[str]] = {}
        total_frames = 0

        for seg_idx, seg in enumerate(segments):
            duration = seg.get("duration", 5)
            seg_frames = self._generate_frames(
                char_image=char_image,
                seg_idx=seg_idx,
                duration=duration,
                fps=fps,
                mode=character_mode,
                seg_type=seg.get("type", "scene"),
            )
            if seg_frames:
                all_frames[str(seg_idx)] = seg_frames
                total_frames += len(seg_frames)

        logger.info(
            f"🎭 Character frames generated: {total_frames} frames "
            f"across {len(all_frames)} segments ({fps}fps)"
        )

        return {
            "character_mode": character_mode,
            "character_frames": all_frames,
            "character_frames_available": len(all_frames) > 0,
            "character_frames_dir": str(self._frames_dir),
            "character_fps": fps,
        }

    def _find_character_image(self, character_images: List[str]) -> Optional[str]:
        """Find the best character image for animation"""
        # Use provided images first
        for img in character_images:
            if os.path.exists(img) and img.lower().endswith(".png"):
                return img

        # Search data/characters/
        char_dir = Path("data/characters")
        if char_dir.exists():
            for ext in ["**/*.png", "**/*.jpg", "**/*.jpeg"]:
                imgs = sorted(char_dir.glob(ext))
                for img in imgs:
                    if "transparent" in img.name.lower():
                        return str(img)
                if imgs:
                    return str(imgs[0])

        return None

    def _build_all_segments(self, scripts: list) -> list:
        """Build all segments across all scripts (same logic as composer._build_segments)"""
        all_segments = []
        for script in scripts:
            hook = script.get("hook", "")
            scenes = script.get("scenes", [])
            cta = script.get("cta", "")

            if hook:
                all_segments.append({
                    "text": hook, "duration": 4, "type": "hook",
                })
            for i, sc in enumerate(scenes):
                all_segments.append({
                    "text": sc.get("text", ""),
                    "duration": sc.get("duration", 5),
                    "type": "scene",
                })
            if cta:
                all_segments.append({
                    "text": cta, "duration": 5, "type": "cta",
                })

        return all_segments

    def _generate_frames(
        self,
        char_image: str,
        seg_idx: int,
        duration: float,
        fps: int,
        mode: str,
        seg_type: str = "scene",
    ) -> List[str]:
        """
        Generate animated frame sequence for one segment.

        Returns list of frame file paths.
        """
        try:
            base = Image.open(char_image).convert("RGBA")
        except Exception as e:
            logger.warning(f"Failed to open character image: {e}")
            return []

        n_frames = max(1, int(duration * fps))
        frames = []

        for frame_i in range(n_frames):
            t = frame_i / n_frames  # 0.0 → 1.0 over the segment

            # Clone the base image
            frame = base.copy()

            if mode == CHARACTER_MODE_TALKING_PET:
                frame = self._animate_pet(frame, t, n_frames)
            elif mode == CHARACTER_MODE_TALKING_AVATAR:
                frame = self._animate_avatar(frame, t, n_frames)

            # Save frame
            frame_path = self._frames_dir / f"char_s{seg_idx:03d}_f{frame_i:03d}.png"
            frame.save(str(frame_path), "PNG")
            frames.append(str(frame_path))

        return frames

    def _animate_pet(self, img: Image.Image, t: float, n_frames: int) -> Image.Image:
        """
        Animate a pet character with:
          - Subtle scale breathing (smooth sine wave)
          - Animated mouth (ellipse that opens/closes with audio rhythm)
          - Eye sparkle (subtle brightness pulse)
        """
        w, h = img.size
        draw = ImageDraw.Draw(img)

        # ── Breathing scale ──
        breathe = 1.0 + 0.03 * math.sin(t * math.pi * 2 * 3)  # 3 cycles
        new_w = int(w * breathe)
        new_h = int(h * breathe)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        # Re-create draw on resized image
        draw = ImageDraw.Draw(img)

        # ── Mouth animation ──
        # Position: bottom-center of the image (assuming face is centered)
        mouth_cx = new_w // 2
        mouth_cy = int(new_h * 0.65)
        mouth_open = 0.3 + 0.4 * abs(math.sin(t * math.pi * 8))  # 8 syllables/sec

        mouth_w = int(new_w * 0.08 * (1.0 + mouth_open))
        mouth_h = int(new_h * 0.02 * (0.5 + mouth_open))

        # Draw mouth — dark ellipse
        draw.ellipse(
            [(mouth_cx - mouth_w, mouth_cy - mouth_h),
             (mouth_cx + mouth_w, mouth_cy + mouth_h)],
            fill=(40, 30, 40, 220),
        )

        # Tongue inside mouth
        if mouth_open > 0.5:
            tongue_h = int(mouth_h * 0.6)
            draw.ellipse(
                [(mouth_cx - mouth_w // 2, mouth_cy),
                 (mouth_cx + mouth_w // 2, mouth_cy + tongue_h)],
                fill=(220, 120, 140, 200),
            )

        # ── Eye sparkle ──
        sparkle = 0.7 + 0.3 * abs(math.sin(t * math.pi * 2))
        eye_y = int(new_h * 0.35)
        for ex in [new_w // 2 - int(new_w * 0.08), new_w // 2 + int(new_w * 0.08)]:
            # White highlight
            draw.ellipse(
                [(ex - 3, eye_y - 3), (ex + 3, eye_y + 3)],
                fill=(255, 255, 255, int(200 * sparkle)),
            )

        return img

    def _animate_avatar(self, img: Image.Image, t: float, n_frames: int) -> Image.Image:
        """
        Animate a human avatar with:
          - Subtle head tilt/nod
          - Mouth movement for lip sync
          - Slight shoulder bounce
        """
        w, h = img.size
        draw = ImageDraw.Draw(img)

        # ── Head nod ──
        nod = 0.02 * math.sin(t * math.pi * 2 * 2.5)  # gentle nodding
        new_h = int(h * (1.0 + nod * 0.5))

        # ── Scale breathing ──
        breathe = 1.0 + 0.015 * math.sin(t * math.pi * 2 * 3)
        new_w = int(w * breathe)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        draw = ImageDraw.Draw(img)

        # ── Mouth animation (more subtle for avatar) ──
        mouth_cx = new_w // 2
        mouth_cy = int(new_h * 0.62)
        talk_cycle = abs(math.sin(t * math.pi * 6))

        # Talking mouth — horizontal ellipse
        mouth_w = int(new_w * 0.04 * (1.0 + talk_cycle * 2))
        mouth_h = int(new_h * 0.012 * (0.3 + talk_cycle * 1.5))

        draw.ellipse(
            [(mouth_cx - mouth_w, mouth_cy - mouth_h),
             (mouth_cx + mouth_w, mouth_cy + mouth_h)],
            fill=(60, 40, 50, 200),
        )

        # ── Eye blink (occasional) ──
        blink_phase = (t * n_frames) % 20
        if blink_phase < 1.5:  # brief blink
            eye_y = int(new_h * 0.35)
            for ex in [new_w // 2 - int(new_w * 0.06), new_w // 2 + int(new_w * 0.06)]:
                draw.line(
                    [(ex - 6, eye_y), (ex + 6, eye_y)],
                    fill=(30, 30, 40, 255), width=2,
                )

        return img
