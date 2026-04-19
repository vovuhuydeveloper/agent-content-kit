"""
ThumbnailAgent — Generate clean, professional video thumbnails.
Dynamic dark gradients, subtle decorations, character behind text.
"""

import glob
import logging
import os
import textwrap
from pathlib import Path
from typing import Any, Dict

from PIL import Image, ImageDraw

from .base import BaseAgent
from .composer.renderer import get_font

logger = logging.getLogger("agent.thumbnail")


class ThumbnailAgent(BaseAgent):
    name = "ThumbnailAgent"
    description = "Generate professional thumbnails"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        videos = context.get("videos", [])
        scripts = context.get("scripts", [])
        character_images = context.get("character_images", [])
        job_dir = Path(context["job_dir"])
        job_id = context.get("job_id", "")

        thumb_dir = job_dir / "thumbnails"
        thumb_dir.mkdir(exist_ok=True)

        # Find character images: job dir → global
        if not character_images:
            job_char_dir = Path(f"data/characters/{job_id}")
            if job_char_dir.exists():
                for ext in ["*.png", "*.jpg", "*.jpeg"]:
                    character_images.extend(glob.glob(str(job_char_dir / ext)))
        if not character_images:
            # Check if char_overlay exists in job dir
            overlay = job_dir / "char_overlay.png"
            if overlay.exists():
                character_images.append(str(overlay))

        if character_images:
            logger.info(f"Character: {os.path.basename(character_images[0])}")

        thumbnails = []
        for video_info in videos:
            script_id = video_info.get("script_id", 1)
            orientation = video_info.get("orientation", "vertical")
            script = next((s for s in scripts if s.get("script_id") == script_id), {})
            title = script.get("title", f"Video {script_id}")
            hook = script.get("hook", "")
            color_scheme = script.get("color_scheme", {})

            thumb_path = thumb_dir / f"thumb_{script_id}.jpg"
            char_image = character_images[0] if character_images else None

            self._create_thumbnail(
                title=title, hook=hook, output_path=thumb_path,
                char_image=char_image, orientation=orientation,
                color_scheme=color_scheme,
            )
            if thumb_path.exists():
                thumbnails.append({"script_id": script_id, "path": str(thumb_path)})
                logger.info(f"Thumbnail: {thumb_path.name}")

        return {"thumbnails": thumbnails, "thumbnail_count": len(thumbnails)}

    def _color(self, data, default):
        if isinstance(data, (list, tuple)) and len(data) >= 3:
            return (int(data[0]), int(data[1]), int(data[2]))
        return default

    def _darken(self, c, factor=0.3):
        """Darken a color for gradient background"""
        return tuple(max(0, int(v * factor)) for v in c)

    def _create_thumbnail(self, title, hook, output_path, char_image,
                          orientation="vertical", color_scheme=None) -> bool:
        if orientation == "vertical":
            w, h = 1080, 1920
        elif orientation == "square":
            w, h = 1080, 1080
        else:
            w, h = 1920, 1080

        cs = color_scheme or {}
        raw_primary = self._color(cs.get("primary"), (60, 120, 200))
        raw_secondary = self._color(cs.get("secondary"), (40, 60, 120))
        accent = self._color(cs.get("accent"), (100, 200, 255))

        # Always use DARK versions for gradient background
        primary = self._darken(raw_primary, 0.25)
        secondary = self._darken(raw_secondary, 0.20)

        # === GRADIENT BACKGROUND ===
        img = Image.new("RGBA", (w, h), (*primary, 255))
        draw = ImageDraw.Draw(img)
        for y in range(h):
            ratio = y / h
            r = int(primary[0] * (1 - ratio) + secondary[0] * ratio)
            g = int(primary[1] * (1 - ratio) + secondary[1] * ratio)
            b = int(primary[2] * (1 - ratio) + secondary[2] * ratio)
            draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

        # Clean background — no distracting decorations

        # === CHARACTER BEHIND TEXT ===
        if char_image and os.path.exists(char_image):
            try:
                char = Image.open(char_image).convert("RGBA")
                if orientation == "vertical":
                    char_w = int(w * 0.55)
                    cx_pos = w - char_w + 10
                else:
                    char_w = int(h * 0.65)
                    cx_pos = w - char_w - 20

                aspect = char.height / char.width
                char_h = int(char_w * aspect)
                char = char.resize((char_w, char_h), Image.LANCZOS)
                cy_pos = h - char_h

                img.paste(char, (cx_pos, cy_pos), char)
            except Exception as e:
                logger.warning(f"Character overlay failed: {e}")

        # Redraw for text
        draw = ImageDraw.Draw(img)

        # === ACCENT BARS ===
        draw.rectangle([(0, 0), (w, 6)], fill=(*accent, 200))
        draw.rectangle([(0, h - 6), (w, h)], fill=(*accent, 200))

        # === TEXT ===
        if orientation == "vertical":
            self._text_vertical(draw, w, h, title, hook, accent)
        else:
            self._text_horizontal(draw, w, h, title, hook, accent)

        img = img.convert("RGB")
        img.save(str(output_path), "JPEG", quality=92)
        return True

    def _outlined_text(self, draw, xy, text, font, fill=(255, 255, 255),
                        outline_color=(0, 0, 0), width=5, **kw):
        """Bold outlined text — readable on any background"""
        x, y = xy
        for dx in range(-width, width + 1):
            for dy in range(-width, width + 1):
                if dx * dx + dy * dy <= width * width:
                    draw.multiline_text((x + dx, y + dy), text, fill=outline_color,
                                        font=font, **kw)
        draw.multiline_text(xy, text, fill=fill, font=font, **kw)

    def _text_vertical(self, draw, w, h, title, hook, accent):
        font_title = get_font(90)
        font_hook = get_font(44)

        # Title — top center, big bold
        wrapped = textwrap.fill(title, width=12)
        try:
            bbox = draw.multiline_textbbox((0, 0), wrapped, font=font_title, align="center")
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = w - 80

        tx = (w - tw) // 2
        ty = int(h * 0.08)
        self._outlined_text(draw, (tx, ty), wrapped, font_title,
                            fill=(255, 255, 255), outline_color=(0, 0, 0),
                            width=6, align="center", spacing=16)

        # Hook — mid left
        if hook:
            wrapped_hook = textwrap.fill(hook, width=24)
            hy = int(h * 0.42)
            hook_color = (min(255, accent[0] + 80), min(255, accent[1] + 80),
                          min(255, accent[2] + 80))
            self._outlined_text(draw, (50, hy), wrapped_hook, font_hook,
                                fill=hook_color, outline_color=(0, 0, 0),
                                width=4, spacing=10)

    def _text_horizontal(self, draw, w, h, title, hook, accent):
        font_title = get_font(72)
        font_hook = get_font(38)

        wrapped = textwrap.fill(title, width=16)
        ty = int(h * 0.12)
        self._outlined_text(draw, (60, ty), wrapped, font_title,
                            fill=(255, 255, 255), outline_color=(0, 0, 0),
                            width=5, spacing=12)

        if hook:
            wrapped_hook = textwrap.fill(hook, width=30)
            hy = int(h * 0.60)
            hook_color = (min(255, accent[0] + 80), min(255, accent[1] + 80),
                          min(255, accent[2] + 80))
            self._outlined_text(draw, (60, hy), wrapped_hook, font_hook,
                                fill=hook_color, outline_color=(0, 0, 0),
                                width=3, spacing=8)

