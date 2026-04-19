"""
VideoComposerAgent — Thin orchestrator that delegates to services.
stock_service → renderer → ffmpeg
"""


import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from ..base import BaseAgent
from .ffmpeg import (
    concat_with_audio,
    create_solid_segment,
    create_stock_segment,
    get_audio_duration,
    image_to_video,
)
from .renderer import create_caption_overlay, create_gradient_frame
from .stock_service import get_stock_for_scene

logger = logging.getLogger("agent.composer")

# Default colors — overridden by AI-generated color_scheme
DEFAULT_COLORS = [
    (26, 10, 62), (15, 26, 62), (10, 30, 50), (35, 10, 45), (10, 40, 40),
]


def _get_scene_colors(script: dict) -> list:
    """Extract colors from AI-generated color_scheme, or use defaults"""
    cs = script.get("color_scheme", {})
    try:
        primary = tuple(cs.get("primary", [26, 10, 62])[:3])
        secondary = tuple(cs.get("secondary", [15, 26, 62])[:3])

        # Generate variations
        return [
            primary,
            secondary,
            tuple(min(255, c + 20) for c in primary),
            tuple(min(255, c + 10) for c in secondary),
            tuple(max(0, (p + s) // 2) for p, s in zip(primary, secondary)),
        ]
    except (TypeError, ValueError):
        return DEFAULT_COLORS


class VideoComposerAgent(BaseAgent):
    name = "VideoComposerAgent"
    description = "Render video: stock footage + character + captions + voiceover"
    max_retries = 2
    is_critical = True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        scripts = context["scripts"]
        voice_files = context["voice_files"]
        character_images = context.get("character_images", [])
        job_dir = Path(context["job_dir"])


        video_dir = job_dir / "videos"
        video_dir.mkdir(exist_ok=True)

        if not character_images:
            # Try job-specific characters first
            job_char_dir = job_dir.parent.parent / "characters" / job_dir.name
            if job_char_dir.exists():
                character_images = [str(f) for f in job_char_dir.glob("*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg')]
            if not character_images:
                character_images = self._find_characters()

        if character_images:
            logger.info(f"Using {len(character_images)} character image(s): {[os.path.basename(p) for p in character_images]}")
        else:
            logger.info("No character images found — video will render without character overlay")

        # Determine video dimensions from aspect_ratio
        aspect_ratio = context.get("aspect_ratio", "9:16")
        if aspect_ratio == "16:9":
            w, h = 1920, 1080
            orientation = "horizontal"
        elif aspect_ratio == "1:1":
            w, h = 1080, 1080
            orientation = "square"
        else:  # 9:16 default
            w, h = 1080, 1920
            orientation = "vertical"
        logger.info(f"Video dimensions: {w}x{h} ({aspect_ratio})")

        pexels_key = os.environ.get("PEXELS_API_KEY", "")
        videos = []

        for script in scripts:
            script_id = script.get("script_id", 1)
            voice = next((v for v in voice_files if v["script_id"] == script_id), None)
            if not voice:
                continue

            voice_path = Path(voice["path"])
            output_path = video_dir / f"video_{script_id}.mp4"

            try:
                audio_dur = get_audio_duration(voice_path)
                char_image = self._pick_character(character_images)
                char_overlay = self._prepare_overlay(char_image, w, h, job_dir)

                success = self._render(
                    script, voice_path, char_overlay, output_path,
                    w, h, audio_dur, orientation, job_dir, pexels_key,
                )

                if success and output_path.exists():
                    size = output_path.stat().st_size
                    videos.append({
                        "script_id": script_id, "path": str(output_path),
                        "title": script.get("title", ""), "file_size": size,
                        "orientation": orientation,
                    })
                    logger.info(f"Video {script_id}: {output_path.name} ({size/1024/1024:.1f}MB)")
            except Exception as e:
                logger.error(f"Video {script_id} failed: {e}")

        return {"videos": videos, "video_count": len(videos), "video_dir": str(video_dir)}

    # ── Helpers ──

    def _find_characters(self) -> List[str]:
        """Find character images — search recursively in data/characters/"""
        char_dir = Path("data/characters")
        if not char_dir.exists():
            return []
        imgs = []
        for ext in ["**/*.png", "**/*.jpg", "**/*.jpeg"]:
            imgs.extend(str(f) for f in char_dir.glob(ext) if f.is_file())
        return sorted(imgs)

    def _pick_character(self, images: List[str]) -> Optional[str]:
        for img in images:
            if "transparent" in img.lower():
                return img
        for img in images:
            if img.lower().endswith(".png"):
                return img
        return images[0] if images else None

    def _prepare_overlay(self, char_image: Optional[str], w: int, h: int, job_dir: Path) -> Optional[str]:
        if not char_image or not os.path.exists(char_image):
            return None
        try:
            img = Image.open(char_image).convert("RGBA")
            char_w = int(w * 0.32)
            char_h = int(char_w * img.height / img.width)
            img = img.resize((char_w, char_h), Image.LANCZOS)

            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            overlay.paste(img, (w - char_w - 20, h - char_h - 200), img)

            path = job_dir / "char_overlay.png"
            overlay.save(str(path), "PNG")
            return str(path)
        except Exception as e:
            logger.warning(f"Character overlay failed: {e}")
            return None

    # ── Main render ──

    def _render(self, script, voice_path, char_overlay, output_path,
                w, h, audio_dur, orientation, job_dir, pexels_key):
        segments = self._build_segments(script, audio_dur)

        # Download stock footage
        stock_dir = job_dir / "stock_clips"
        stock_dir.mkdir(exist_ok=True)
        stock_clips = {}

        if pexels_key:
            logger.info("Downloading stock footage from Pexels...")
            for idx, seg in enumerate(segments):
                clip = get_stock_for_scene(
                    seg["text"], seg.get("visual", ""), idx,
                    stock_dir, orientation, pexels_key,
                )
                if clip:
                    stock_clips[idx] = clip
            logger.info(f"Downloaded {len(stock_clips)}/{len(segments)} stock clips")

        # Render each segment
        temp_dir = job_dir / "temp_render"
        temp_dir.mkdir(exist_ok=True)
        video_segments = []

        for idx, seg in enumerate(segments):
            seg_out = temp_dir / f"seg_{idx:03d}.mp4"
            dur = seg["duration"]
            stock = stock_clips.get(idx)

            if stock and stock.exists():
                caption = create_caption_overlay(
                    seg["text"], w, h, seg["type"],
                    seg.get("num", 0), seg.get("total", 0),
                )
                cap_path = temp_dir / f"cap_{idx:03d}.png"
                caption.save(str(cap_path), "PNG")
                ok = create_stock_segment(stock, cap_path, char_overlay, seg_out, w, h, dur)
            else:
                scene_colors = _get_scene_colors(script)
                bg = scene_colors[idx % len(scene_colors)]
                # Get accent color for decorations
                cs = script.get("color_scheme", {})
                accent = tuple(cs.get("accent", [124, 77, 255])[:3])
                frame = create_gradient_frame(
                    seg["text"], w, h, bg, seg["type"],
                    seg.get("num", 0), seg.get("total", 0), char_overlay,
                    accent_color=accent,
                )
                frame_path = temp_dir / f"frame_{idx:03d}.png"
                frame.save(str(frame_path), "PNG")
                ok = image_to_video(frame_path, seg_out, dur)

            if ok and seg_out.exists():
                video_segments.append(str(seg_out))
            else:
                if create_solid_segment(seg_out, w, h, dur):
                    video_segments.append(str(seg_out))

        if not video_segments:
            return False

        result = concat_with_audio(video_segments, voice_path, output_path, temp_dir)

        # Cleanup
        for f in temp_dir.glob("*"):
            f.unlink(missing_ok=True)
        temp_dir.rmdir()

        return result

    def _build_segments(self, script, audio_dur):
        segments = []
        hook = script.get("hook", "")
        scenes = script.get("scenes", [])
        cta = script.get("cta", "")

        if hook:
            segments.append({"text": hook, "duration": 4, "type": "hook", "visual": ""})
        for i, sc in enumerate(scenes):
            segments.append({
                "text": sc.get("text", ""), "duration": sc.get("duration", 5),
                "type": "scene", "num": i + 1, "total": len(scenes),
                "visual": sc.get("visual", ""),
            })
        if cta:
            segments.append({"text": cta, "duration": 5, "type": "cta", "visual": ""})

        total_dur = sum(s["duration"] for s in segments)
        if audio_dur > 0 and total_dur > 0:
            ratio = audio_dur / total_dur
            for s in segments:
                s["duration"] = max(2, s["duration"] * ratio)

        return segments
