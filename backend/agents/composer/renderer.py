"""
Text Renderer — Premium TikTok/Shorts-style caption overlays.

Design philosophy (based on trending short-form video styles):
  - Clean subtitle bar at bottom center (not full-width dump)
  - Bold Montserrat/BeVietnam font with text stroke for readability
  - Subtle glass-morphism text container (rounded, blurred BG)
  - Minimal progress indicator (dot-based, not progress bar)
  - No bulky logos — clean watermark only
  - AI background images should breathe — minimal overlays
"""

import logging
import math
import os
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger("agent.composer.renderer")

# Project root for bundled fonts
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Font search paths — priority order
FONT_PATHS_BOLD = [
    str(_PROJECT_ROOT / "data" / "fonts" / "Montserrat-ExtraBold.ttf"),
    str(_PROJECT_ROOT / "data" / "fonts" / "Montserrat-Bold.ttf"),
    str(_PROJECT_ROOT / "data" / "fonts" / "BeVietnamPro-Bold.ttf"),
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

FONT_PATHS_REGULAR = [
    str(_PROJECT_ROOT / "data" / "fonts" / "Montserrat-SemiBold.ttf"),
    str(_PROJECT_ROOT / "data" / "fonts" / "BeVietnamPro-Bold.ttf"),
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

_font_cache: dict = {}


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Get a font that supports Vietnamese diacritics"""
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]

    paths = FONT_PATHS_BOLD if bold else FONT_PATHS_REGULAR
    for fp in paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, size)
                _font_cache[key] = font
                return font
            except Exception:
                continue

    logger.warning("No TrueType font found — using default")
    return ImageFont.load_default()


def _draw_text_with_stroke(
    draw: ImageDraw.Draw, pos: Tuple[int, int], text: str,
    font: ImageFont.FreeTypeFont, fill=(255, 255, 255),
    stroke_color=(0, 0, 0), stroke_width=3, **kwargs
):
    """Draw text with outline stroke for readability over any background"""
    x, y = pos
    draw.multiline_text(
        (x, y), text, font=font, fill=fill,
        stroke_width=stroke_width, stroke_fill=stroke_color, **kwargs
    )


def _create_glass_panel(w: int, h: int, radius: int = 30,
                        bg_color=(0, 0, 0, 140)) -> Image.Image:
    """Create a glassmorphism-style rounded panel"""
    panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle([(0, 0), (w - 1, h - 1)],
                           radius=radius, fill=bg_color)
    return panel


def create_caption_overlay(
    text: str, w: int, h: int,
    seg_type: str = "scene",
    scene_num: int = 0, total: int = 0,
) -> Image.Image:
    """
    Create transparent PNG with premium caption text overlay.

    Style: Trending TikTok/Shorts layout
      - Centered subtitle panel at bottom
      - Bold text with stroke outline
      - Clean dot-based progress indicator
      - Subtle brand watermark
    """
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # === BOTTOM: Subtitle panel ===
    font_size = 52 if w < 1200 else 48
    font_main = get_font(font_size, bold=True)

    # Wrap text — shorter lines for readability
    max_chars = 18 if w < 1200 else 28
    wrapped = textwrap.fill(text, width=max_chars)
    lines = wrapped.split("\n")

    # Calculate text block size
    line_spacing = 12
    line_height = font_size + line_spacing
    text_block_h = line_height * len(lines)
    panel_padding_y = 30

    # Panel dimensions
    panel_h = text_block_h + panel_padding_y * 2
    panel_w = w - 80  # Leave margins
    panel_x = 40
    panel_y = h - panel_h - 120  # Leave space from bottom for TikTok UI

    # Draw glass panel background
    glass = _create_glass_panel(panel_w, panel_h, radius=24,
                                bg_color=(0, 0, 0, 130))
    img.paste(glass, (panel_x, panel_y), glass)

    # Draw text with stroke — centered in panel
    text_y = panel_y + panel_padding_y
    for line in lines:
        try:
            tw = draw.textlength(line, font=font_main)
        except Exception:
            tw = len(line) * font_size * 0.5
        text_x = panel_x + (panel_w - tw) // 2
        _draw_text_with_stroke(
            draw, (int(text_x), text_y), line,
            font=font_main, fill=(255, 255, 255),
            stroke_color=(0, 0, 0), stroke_width=4,
        )
        text_y += line_height

    # === TOP: Progress & Branding ===
    if seg_type == "hook":
        brand_name = os.environ.get("BRAND_NAME", "")
        if brand_name:
            font_brand = get_font(26, bold=True)
            try:
                bw = draw.textlength(brand_name, font=font_brand)
            except Exception:
                bw = len(brand_name) * 14
            # Pill-shaped brand badge — top center
            badge_w = int(bw) + 40
            badge_h = 42
            badge_x = (w - badge_w) // 2
            badge_y = 55
            badge = _create_glass_panel(badge_w, badge_h, radius=21,
                                        bg_color=(255, 255, 255, 30))
            img.paste(badge, (badge_x, badge_y), badge)
            _draw_text_with_stroke(
                draw, (badge_x + 20, badge_y + 8), brand_name,
                font=font_brand, fill=(255, 255, 255, 230),
                stroke_width=2, stroke_color=(0, 0, 0),
            )

    elif seg_type == "scene" and total > 0:
        # Dot-based progress indicator — top center
        dot_radius = 5
        dot_spacing = 20
        total_dots_w = total * dot_spacing
        start_x = (w - total_dots_w) // 2
        dot_y = 55

        for i in range(1, total + 1):
            cx = start_x + (i - 1) * dot_spacing + dot_radius
            if i <= scene_num:
                # Active dot — white filled
                draw.ellipse(
                    [(cx - dot_radius, dot_y - dot_radius),
                     (cx + dot_radius, dot_y + dot_radius)],
                    fill=(255, 255, 255, 255)
                )
            else:
                # Inactive dot — dim
                draw.ellipse(
                    [(cx - dot_radius, dot_y - dot_radius),
                     (cx + dot_radius, dot_y + dot_radius)],
                    fill=(255, 255, 255, 80)
                )

    elif seg_type == "cta":
        # CTA — accent colored pill at top
        cta_label = "👆 Theo dõi ngay"
        font_cta = get_font(28, bold=True)
        try:
            cta_w = draw.textlength(cta_label, font=font_cta)
        except Exception:
            cta_w = 180
        pill_w = int(cta_w) + 50
        pill_h = 48
        pill_x = (w - pill_w) // 2
        pill_y = 50
        # Accent pill
        draw.rounded_rectangle(
            [(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
            radius=24, fill=(99, 102, 241, 230)  # Indigo
        )
        draw.text(
            (pill_x + 25, pill_y + 10), cta_label,
            fill=(255, 255, 255), font=font_cta,
        )

    return img


def create_gradient_frame(
    text: str, w: int, h: int,
    bg_color: Tuple[int, int, int],
    seg_type: str = "scene",
    scene_num: int = 0, total: int = 0,
    char_overlay_path: Optional[str] = None,
    accent_color: Tuple[int, int, int] = (99, 102, 241),
) -> Image.Image:
    """
    Create a premium scene frame with gradient bg + text.
    Used as fallback when no AI image or stock footage available.
    """
    img = Image.new("RGBA", (w, h), bg_color + (255,))
    draw = ImageDraw.Draw(img)

    # Premium gradient background
    for y in range(h):
        ratio = y / h
        if ratio < 0.3:
            t = ratio / 0.3
            r = int(bg_color[0] * (1 - t * 0.3))
            g = int(bg_color[1] * (1 - t * 0.3))
            b = int(bg_color[2] * (1 - t * 0.2))
        elif ratio < 0.7:
            t = (ratio - 0.3) / 0.4
            r = int(bg_color[0] * 0.7 + accent_color[0] * 0.15 * t)
            g = int(bg_color[1] * 0.7 + accent_color[1] * 0.15 * t)
            b = int(bg_color[2] * 0.8 + accent_color[2] * 0.15 * t)
        else:
            t = (ratio - 0.7) / 0.3
            r = min(255, int(bg_color[0] * 0.6 + 20 * t))
            g = min(255, int(bg_color[1] * 0.6 + 10 * t))
            b = min(255, int(bg_color[2] * 0.7 + 15 * t))
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    # Subtle noise texture via soft circles
    for cx, cy, radius, alpha in [
        (int(w * 0.8), int(h * 0.2), 250, 15),
        (int(w * 0.15), int(h * 0.6), 200, 12),
        (int(w * 0.5), int(h * 0.85), 180, 10),
    ]:
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse(
            [(cx - radius, cy - radius), (cx + radius, cy + radius)],
            fill=(accent_color[0], accent_color[1], accent_color[2], alpha),
        )
        glow = glow.filter(ImageFilter.GaussianBlur(radius=60))
        img = Image.alpha_composite(img, glow)

    # Create caption overlay and composite
    caption = create_caption_overlay(text, w, h, seg_type, scene_num, total)
    img = Image.alpha_composite(img, caption)

    # Character overlay
    if char_overlay_path and os.path.exists(char_overlay_path):
        try:
            overlay = Image.open(char_overlay_path).convert("RGBA")
            img = Image.alpha_composite(img, overlay)
        except Exception:
            pass

    return img.convert("RGB")


# ── Audio-Synced Captions ──

def create_word_timing_captions(
    text: str,
    w: int,
    h: int,
    segment_duration: float,
    seg_type: str = "scene",
    scene_num: int = 0,
    total: int = 0,
    fps: int = 4,
) -> List[Image.Image]:
    """
    Create a sequence of caption frames with progressive word highlighting.

    TikTok/Shorts style: words appear left-to-right, current word is
    highlighted in bright accent color, spoken words fade slightly.

    Args:
        text: The full caption text for this segment
        w, h: Video dimensions
        segment_duration: Duration of this segment in seconds
        fps: How many caption frames per second (default 4 = every 250ms)

    Returns:
        List of PIL Images, one per timing step. Each image shows the
        full text with the current word highlighted.
    """
    if not text or not text.strip():
        return []

    # Tokenize into words (keep punctuation attached)
    words = [w for w in text.split() if w.strip()]
    if not words:
        return []

    n_words = len(words)
    # Number of frames = segment_duration * fps, at least one per word
    n_frames = max(n_words, int(segment_duration * fps))

    # Font config
    font_size = 52 if w < 1200 else 48
    font_main = get_font(font_size, bold=True)

    # Color palette
    active_fill = (255, 255, 80)     # Bright yellow — current word
    spoken_fill = (255, 255, 255)    # White — already spoken
    pending_fill = (180, 180, 200)   # Dim gray — not yet spoken
    stroke_color = (0, 0, 0)
    stroke_width = 4

    # Panel layout (same as create_caption_overlay)
    max_chars = 18 if w < 1200 else 28
    wrapped = textwrap.fill(text, width=max_chars)
    lines = wrapped.split("\n")

    line_spacing = 12
    line_height = font_size + line_spacing
    text_block_h = line_height * len(lines)
    panel_padding_y = 30
    panel_h = text_block_h + panel_padding_y * 2
    panel_w = w - 80
    panel_x = 40
    panel_y = h - panel_h - 120

    frames: List[Image.Image] = []

    # Build word-to-position mapping
    word_positions = _build_word_positions(
        words, lines, font_main, font_size, line_spacing,
        panel_x, panel_y, panel_w, panel_padding_y, w,
    )

    for frame_idx in range(n_frames):
        # Which word is currently being spoken?
        word_idx = min(int(frame_idx * n_words / n_frames), n_words - 1)

        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Glass panel background
        glass = _create_glass_panel(panel_w, panel_h, radius=24,
                                    bg_color=(0, 0, 0, 130))
        img.paste(glass, (panel_x, panel_y), glass)

        # Draw each word with appropriate color
        for wi, (wx, wy, word_text) in enumerate(word_positions):
            if wi < word_idx:
                fill = spoken_fill
            elif wi == word_idx:
                fill = active_fill
            else:
                fill = pending_fill

            _draw_text_with_stroke(
                draw, (int(wx), int(wy)), word_text,
                font=font_main, fill=fill,
                stroke_color=stroke_color, stroke_width=stroke_width,
            )

        # Progress indicator
        if total > 0:
            dot_radius = 5
            dot_spacing = 20
            total_dots_w = total * dot_spacing
            start_x = (w - total_dots_w) // 2
            dot_y = 55
            for i in range(1, total + 1):
                cx = start_x + (i - 1) * dot_spacing + dot_radius
                if i <= scene_num:
                    draw.ellipse(
                        [(cx - dot_radius, dot_y - dot_radius),
                         (cx + dot_radius, dot_y + dot_radius)],
                        fill=(255, 255, 255, 255)
                    )
                else:
                    draw.ellipse(
                        [(cx - dot_radius, dot_y - dot_radius),
                         (cx + dot_radius, dot_y + dot_radius)],
                        fill=(255, 255, 255, 80)
                    )

        frames.append(img)

    return frames


def _build_word_positions(
    words: List[str],
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    font_size: int,
    line_spacing: int,
    panel_x: int,
    panel_y: int,
    panel_w: int,
    panel_padding_y: int,
    video_w: int,
) -> List[Tuple[float, float, str]]:
    """
    Map each word to its (x, y) pixel position within the caption panel.

    Words are laid out left-to-right across lines with word spacing.
    """
    positions: List[Tuple[float, float, str]] = []
    word_idx = 0
    space_width = font_size * 0.3

    for line_idx, line in enumerate(lines):
        line_words = line.split()
        y = panel_y + panel_padding_y + line_idx * (font_size + line_spacing)

        try:
            dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
            line_word_widths = [
                dummy_draw.textlength(w, font=font) for w in line_words
            ]
        except Exception:
            line_word_widths = [len(w) * font_size * 0.5 for w in line_words]

        total_line_w = sum(line_word_widths) + space_width * (len(line_words) - 1)

        # Center the line horizontally
        start_x = panel_x + (panel_w - total_line_w) / 2

        x = start_x
        for wi, word in enumerate(line_words):
            if word_idx < len(words):
                positions.append((x, y, word))
                word_idx += 1
                x += line_word_widths[wi] + space_width

    return positions


def create_thumbnail(
    title: str, hook: str, w: int, h: int,
    char_image: Optional[str] = None,
) -> Image.Image:
    """
    Create premium 9:16 thumbnail.
    Style: Clean, bold text, accent color, character overlay.
    """
    img = Image.new("RGBA", (w, h), (15, 15, 35, 255))
    draw = ImageDraw.Draw(img)

    # Premium dark gradient
    for y in range(h):
        ratio = y / h
        r = int(15 + 25 * ratio)
        g = int(15 + 10 * ratio)
        b = int(35 + 30 * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    # Accent glow at top
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        [(w // 2 - 300, -200), (w // 2 + 300, 200)],
        fill=(99, 102, 241, 40),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=80))
    img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)

    # Top accent line
    draw.rectangle([(0, 0), (w, 4)], fill=(99, 102, 241))

    font_big = get_font(56 if w < h else 48, bold=True)
    font_hook = get_font(34 if w < h else 28, bold=False)
    font_brand = get_font(24, bold=True)

    # Title — centered, bold, with stroke
    wrapped_title = textwrap.fill(title, width=14)
    bbox = draw.multiline_textbbox((0, 0), wrapped_title,
                                   font=font_big, align="center")
    tw = bbox[2] - bbox[0]
    title_y = int(h * 0.10)
    _draw_text_with_stroke(
        draw, ((w - tw) // 2, title_y), wrapped_title,
        font=font_big, fill=(255, 255, 255),
        stroke_width=4, stroke_color=(0, 0, 0),
        align="center", spacing=16,
    )

    # Hook subtitle
    if hook:
        wrapped_hook = textwrap.fill(hook, width=20)
        bbox2 = draw.multiline_textbbox((0, 0), wrapped_hook,
                                        font=font_hook, align="center")
        hw = bbox2[2] - bbox2[0]
        hook_y = int(h * 0.42)
        hh = bbox2[3] - bbox2[1] + 30
        panel = _create_glass_panel(hw + 60, hh, radius=20,
                                    bg_color=(99, 102, 241, 50))
        img.paste(panel, ((w - hw - 60) // 2, hook_y - 15), panel)
        draw = ImageDraw.Draw(img)
        _draw_text_with_stroke(
            draw, ((w - hw) // 2, hook_y), wrapped_hook,
            font=font_hook, fill=(220, 210, 255),
            stroke_width=2, stroke_color=(0, 0, 0),
            align="center", spacing=10,
        )

    # Brand watermark — bottom, subtle
    brand_name = os.environ.get("BRAND_NAME", "")
    if brand_name:
        try:
            bw = draw.textlength(brand_name, font=font_brand)
        except Exception:
            bw = len(brand_name) * 14
        brand_y = h - 280
        badge = _create_glass_panel(int(bw) + 50, 40, radius=20,
                                    bg_color=(99, 102, 241, 180))
        img.paste(badge, ((w - int(bw) - 50) // 2, brand_y), badge)
        draw = ImageDraw.Draw(img)
        draw.text(((w - bw) // 2, brand_y + 8), brand_name,
                  fill=(255, 255, 255), font=font_brand)

    # Character overlay
    if char_image and os.path.exists(char_image):
        try:
            char = Image.open(char_image).convert("RGBA")
            char_w = int(w * 0.4)
            char_h = int(char_w * char.height / char.width)
            char = char.resize((char_w, char_h), Image.LANCZOS)
            cx, cy = w - char_w - 30, h - char_h - 40
            img.paste(char, (cx, cy), char)
        except Exception as e:
            logger.warning(f"Character overlay failed: {e}")

    return img.convert("RGB")


# ═══════════════════════════════════════════════════════════
# TikTok Meme & Reaction Templates
# ═══════════════════════════════════════════════════════════

MEME_COLORS = [
    (255, 59, 48),   # Red
    (255, 149, 0),   # Orange
    (255, 204, 0),   # Yellow
    (52, 199, 89),   # Green
    (0, 122, 255),   # Blue
    (175, 82, 222),  # Purple
    (255, 45, 85),   # Pink
]


def create_meme_caption(text, w, h, position="center", color_idx=0, emoji=""):
    """Create TikTok meme-style caption: bold text on colored bar with emoji."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = MEME_COLORS[color_idx % len(MEME_COLORS)]
    font_size = 64 if w < 1200 else 56
    font = get_font(font_size, bold=True)
    display_text = text.strip().upper()
    if emoji:
        display_text = f"{emoji} {display_text} {emoji}"
    max_chars = 12 if w < 1200 else 20
    if len(display_text) > max_chars:
        display_text = textwrap.shorten(display_text, width=max_chars, placeholder="…")
    wrapped = textwrap.fill(display_text, width=max_chars)
    lines = wrapped.split("\n")[:2]
    try:
        line_widths = [draw.textlength(ln, font=font) for ln in lines]
        max_line_w = max(line_widths) if line_widths else 0
        line_height = font_size + 10
        text_block_h = line_height * len(lines)
    except Exception:
        max_line_w = len(max(lines, key=len)) * font_size * 0.6
        text_block_h = font_size * len(lines) * 1.2
    bar_padding_x, bar_padding_y = 60, 30
    bar_w = int(max_line_w + bar_padding_x * 2)
    bar_h = int(text_block_h + bar_padding_y * 2)
    bar_x = (w - bar_w) // 2
    if position == "top":
        bar_y = int(h * 0.08)
    elif position == "bottom":
        bar_y = h - bar_h - int(h * 0.15)
    else:
        bar_y = (h - bar_h) // 2
    draw.rounded_rectangle(
        [(bar_x + 6, bar_y + 6), (bar_x + bar_w + 6, bar_y + bar_h + 6)],
        radius=20, fill=(0, 0, 0, 100),
    )
    draw.rounded_rectangle(
        [(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)],
        radius=20, fill=color + (240,),
    )
    text_y = bar_y + bar_padding_y
    for line in lines:
        try:
            lw = draw.textlength(line, font=font)
        except Exception:
            lw = len(line) * font_size * 0.5
        tx = bar_x + (bar_w - lw) // 2
        draw.text((tx + 2, text_y + 2), line, fill=(0, 0, 0, 180), font=font)
        draw.text((tx, text_y), line, fill=(255, 255, 255), font=font)
        text_y += line_height
    return img


def create_reaction_cut(w, h, effect="zoom_in", duration=1.5, n_frames=8):
    """Create reaction cut frame sequence: zoom, flash, or shake effect."""
    frames = []
    for i in range(n_frames):
        t = i / max(n_frames - 1, 1)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        if effect == "flash":
            alpha = int(180 * (1.0 - abs(2 * t - 1)))
            draw.rectangle([(0, 0), (w, h)], fill=(255, 255, 255, alpha))
        elif effect == "shake":
            shake_x = int(30 * math.sin(t * math.pi * 8) * (1 - t))
            bar_w = int(w * 0.15)
            color = MEME_COLORS[i % len(MEME_COLORS)]
            draw.rectangle([(shake_x, 0), (shake_x + bar_w, h)], fill=color + (150,))
            draw.rectangle([(w - shake_x - bar_w, 0), (w - shake_x, h)], fill=color + (150,))
        elif effect in ("zoom_in", "zoom_out"):
            vignette_alpha = int(120 * (t if effect == "zoom_in" else (1 - t)))
            for y in range(h):
                edge_dist = min(y, h - y) / (h * 0.3)
                fade = min(1.0, edge_dist)
                alpha = int(vignette_alpha * (1 - fade))
                if alpha > 0:
                    draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        frames.append(img)
    return frames
