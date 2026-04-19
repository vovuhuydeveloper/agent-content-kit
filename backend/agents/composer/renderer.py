"""
Text Renderer — PIL-based text/caption rendering for Vietnamese support.
"""

import logging
import os
import textwrap
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("agent.composer.renderer")

# Project root for bundled fonts
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Font search paths — priority order (bundled Vietnamese font first)
FONT_PATHS = [
    # Bundled Vietnamese font (Google Fonts — Be Vietnam Pro Bold)
    str(_PROJECT_ROOT / "data" / "fonts" / "BeVietnamPro-Bold.ttf"),
    # macOS system fonts
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/ArialHB.ttc",
    "/System/Library/Fonts/Avenir Next.ttc",
    "/System/Library/Fonts/SFNS.ttf",
    # Linux system fonts
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

_font_cache: dict = {}


def get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font that supports Vietnamese diacritics"""
    if size in _font_cache:
        return _font_cache[size]

    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, size)
                _font_cache[size] = font
                logger.debug(f"Using font: {os.path.basename(fp)} size={size}")
                return font
            except Exception:
                continue

    logger.warning("No TrueType font found — using default (Vietnamese may not render)")
    return ImageFont.load_default()


def create_caption_overlay(
    text: str, w: int, h: int,
    seg_type: str = "scene",
    scene_num: int = 0, total: int = 0,
) -> Image.Image:
    """Create transparent PNG with caption text overlay"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_main = get_font(80)
    font_badge = get_font(36)

    # Dark gradient at bottom for text readability
    caption_h = int(h * 0.40)
    caption_y = h - caption_h
    for y in range(caption_y, h):
        alpha = int(220 * ((y - caption_y) / caption_h))
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, min(alpha, 220)))

    # Caption text — large TikTok style
    wrapped = textwrap.fill(text, width=16 if w < 1200 else 26)
    draw.multiline_text((50, caption_y + 40), wrapped,
                        fill=(255, 255, 255, 255), font=font_main, spacing=20)

    # Top elements
    if seg_type == "hook":
        brand_name = os.environ.get("BRAND_NAME", "")
        if brand_name:
            try:
                bw = draw.textlength(brand_name, font=font_badge)
            except Exception:
                bw = 60
            draw.rounded_rectangle([(w//2 - int(bw/2) - 20, 30), (w//2 + int(bw/2) + 20, 70)],
                                   radius=20, fill=(124, 77, 255, 200))
            draw.text(((w - bw) // 2, 38), brand_name, fill=(255, 255, 255), font=font_badge)

    elif seg_type == "scene" and total > 0:
        bar_w = w - 40
        progress = int(bar_w * (scene_num / total))
        draw.rectangle([(20, 15), (20 + bar_w, 22)], fill=(255, 255, 255, 60))
        draw.rectangle([(20, 15), (20 + progress, 22)], fill=(124, 77, 255, 230))
        draw.text((w - 80, 30), f"{scene_num}/{total}",
                  fill=(255, 255, 255, 180), font=font_badge)

    elif seg_type == "cta":
        cta_text = "GET IT NOW!"
        draw.rounded_rectangle([(w//2 - 100, 30), (w//2 + 100, 70)],
                               radius=20, fill=(124, 77, 255, 200))
        try:
            bw = draw.textlength(cta_text, font=font_badge)
        except Exception:
            bw = 80
        draw.text(((w - bw) // 2, 38), cta_text, fill=(255, 255, 255), font=font_badge)

    return img


def create_gradient_frame(
    text: str, w: int, h: int,
    bg_color: Tuple[int, int, int],
    seg_type: str = "scene",
    scene_num: int = 0, total: int = 0,
    char_overlay_path: Optional[str] = None,
    accent_color: Tuple[int, int, int] = (124, 77, 255),
) -> Image.Image:
    """Create a full scene frame with gradient bg + text (fallback when no stock footage)"""
    img = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # Multi-stop gradient background
    for y in range(h):
        ratio = y / h
        if ratio < 0.5:
            r = int(bg_color[0] * (1 - ratio) + accent_color[0] * ratio * 0.3)
            g = int(bg_color[1] * (1 - ratio) + accent_color[1] * ratio * 0.3)
            b = int(bg_color[2] * (1 - ratio) + accent_color[2] * ratio * 0.3)
        else:
            r = min(255, bg_color[0] + int(50 * ratio))
            g = min(255, bg_color[1] + int(25 * ratio))
            b = min(255, bg_color[2] + int(35 * ratio))
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Decorative geometric elements
    ac = accent_color
    # Top accent bar
    draw.rectangle([(0, 0), (w, 6)], fill=ac)
    # Corner accent circles
    for cx, cy, radius in [(int(w*0.85), int(h*0.15), 80), (int(w*0.1), int(h*0.75), 50)]:
        draw.ellipse([(cx-radius, cy-radius), (cx+radius, cy+radius)],
                     fill=(ac[0], ac[1], ac[2], 40), outline=None)
    # Diagonal lines for visual interest
    for i in range(0, w + h, 120):
        draw.line([(i, 0), (i - h//3, h)], fill=(255, 255, 255, 8), width=1)

    font_main = get_font(72)
    font_small = get_font(36)

    # Centered text with shadow
    wrapped = textwrap.fill(text, width=20 if w < 1200 else 30)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font_main, align="center")
    tw = bbox[2] - bbox[0]
    tx = (w - tw) // 2
    ty = int(h * 0.15)
    # Shadow
    draw.multiline_text((tx + 3, ty + 3), wrapped, fill=(0, 0, 0),
                        font=font_main, align="center", spacing=14)
    # Main text
    draw.multiline_text((tx, ty), wrapped, fill=(255, 255, 255),
                        font=font_main, align="center", spacing=14)

    # Bottom gradient bar for branding area
    for y in range(h - 120, h):
        alpha = int(180 * ((y - (h - 120)) / 120))
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, min(alpha, 180)))

    if seg_type == "scene" and total > 0:
        bar_w = w - 80
        progress = int(bar_w * (scene_num / total))
        draw.rectangle([(40, 25), (40 + bar_w, 32)], fill=(255, 255, 255, 30))
        draw.rectangle([(40, 25), (40 + progress, 32)], fill=ac)
        draw.text((w - 80, 40), f"{scene_num}/{total}", fill=(200, 200, 200), font=font_small)

    brand_name = os.environ.get("BRAND_NAME", "")
    if brand_name:
        draw.rounded_rectangle(
            [(30, h - 100), (max(200, len(brand_name) * 12 + 60), h - 60)],
            radius=20, fill=(ac[0], ac[1], ac[2]),
        )
        draw.text((50, h - 95), brand_name, fill=(255, 255, 255), font=font_small)

    # Character overlay
    if char_overlay_path and os.path.exists(char_overlay_path):
        try:
            overlay = Image.open(char_overlay_path).convert("RGBA")
            img.paste(overlay, (0, 0), overlay)
        except Exception:
            pass

    return img


def create_thumbnail(
    title: str, hook: str, w: int, h: int,
    char_image: Optional[str] = None,
) -> Image.Image:
    """Create 9:16 thumbnail with title + character"""
    img = Image.new("RGB", (w, h), (26, 10, 62))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        draw.line([(0, y), (w, y)], fill=(
            int(26 + 30 * y / h), int(10 + 15 * y / h), int(62 + 40 * y / h)))

    draw.rectangle([(0, 0), (w, 10)], fill=(124, 77, 255))

    font_big = get_font(60 if w < h else 50)
    font_hook = get_font(38 if w < h else 32)
    font_brand = get_font(28)

    wrapped_title = textwrap.fill(title, width=16)
    bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=font_big, align="center")
    tw = bbox[2] - bbox[0]
    draw.multiline_text(((w - tw) // 2 + 3, int(h * 0.12) + 3), wrapped_title,
                        fill=(0, 0, 0), font=font_big, align="center", spacing=14)
    draw.multiline_text(((w - tw) // 2, int(h * 0.12)), wrapped_title,
                        fill=(255, 255, 255), font=font_big, align="center", spacing=14)

    if hook:
        wrapped_hook = textwrap.fill(hook, width=22)
        bbox2 = draw.multiline_textbbox((0, 0), wrapped_hook, font=font_hook, align="center")
        hw = bbox2[2] - bbox2[0]
        draw.multiline_text(((w - hw) // 2, int(h * 0.45)), wrapped_hook,
                            fill=(200, 180, 255), font=font_hook, align="center", spacing=10)

    brand_name = os.environ.get("BRAND_NAME", "")
    if brand_name:
        try:
            bw = draw.textlength(brand_name, font=font_brand)
        except Exception:
            bw = 80
        draw.rounded_rectangle([(w//2 - int(bw/2) - 40, h - 300), (w//2 + int(bw/2) + 40, h - 250)],
                               radius=25, fill=(124, 77, 255))
        draw.text(((w - bw) // 2, h - 290), brand_name, fill=(255, 255, 255), font=font_brand)

    if char_image and os.path.exists(char_image):
        try:
            char = Image.open(char_image).convert("RGBA")
            char_w = int(w * 0.4)
            char_h = int(char_w * char.height / char.width)
            char = char.resize((char_w, char_h), Image.LANCZOS)
            cx, cy = w - char_w - 30, h - char_h - 40
            if char.mode == "RGBA":
                img.paste(char, (cx, cy), char)
            else:
                img.paste(char, (cx, cy))
        except Exception as e:
            logger.warning(f"Character overlay failed: {e}")

    return img.convert("RGB")
