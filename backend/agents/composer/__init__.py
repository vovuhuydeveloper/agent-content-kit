"""
VideoComposerAgent — Thin orchestrator that delegates to services.
stock_service → renderer → ffmpeg
"""


import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw

from ..base import BaseAgent
from .ffmpeg import (
    concat_with_xfade,
    create_solid_segment,
    create_stock_segment,
    get_audio_duration,
    image_to_video,
    image_to_video_kenburns,
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
        # Animated character frames (from CharacterAgent)
        character_frames = context.get("character_frames", {})
        character_frames_available = context.get("character_frames_available", False)
        if character_frames_available:
            logger.info(f"🎭 Using animated character frames across {len(character_frames)} segments")
        job_dir = Path(context["job_dir"])
        niche = context.get("niche", "")

        # AI-generated video clips from Kling/Runway (if available)
        ai_videos = context.get("ai_videos", {})
        ai_videos_available = context.get("ai_videos_available", False)
        if ai_videos_available:
            logger.info(
                f"🎬 Using {context.get('ai_videos_count', 0)} AI-generated video clips"
            )

        # AI-generated images from Pixelle-Video (if available)
        ai_images = context.get("ai_images", {})
        ai_images_available = context.get("ai_images_available", False)
        if ai_images_available:
            logger.info(f"🎨 Using {context.get('ai_images_count', 0)} AI-generated images")

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

            # Get AI videos for this script (if available)
            script_ai_videos = ai_videos.get(str(script_id), []) if ai_videos_available else []
            # Get AI images for this script (if available)
            script_ai_images = ai_images.get(str(script_id), []) if ai_images_available else []

            try:
                audio_dur = get_audio_duration(voice_path)
                char_image = self._pick_character(character_images)
                char_overlay = self._prepare_overlay(char_image, w, h, job_dir)

                success = self._render(
                    script, voice_path, char_overlay, output_path,
                    w, h, audio_dur, orientation, job_dir, pexels_key,
                    script_ai_videos=script_ai_videos, script_ai_images=script_ai_images, character_frames=character_frames,
                    niche=niche,
                )

                if success and output_path.exists():
                    size = output_path.stat().st_size
                    videos.append({
                        "script_id": script_id, "path": str(output_path),
                        "title": script.get("title", ""), "file_size": size,
                        "orientation": orientation,
                        "used_ai_videos": len(script_ai_videos) > 0, "used_ai_images": len(script_ai_images) > 0,
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
        """
        Prepare logo/character overlay with automatic background removal.

        Positions logo at top-center with proper sizing — never overlaps captions.
        Auto-removes solid backgrounds (white, near-white, uniform colors).
        """
        if not char_image or not os.path.exists(char_image):
            return None
        try:
            img = Image.open(char_image).convert("RGBA")

            # Auto-remove background if image has solid/uniform background
            img = self._remove_background(img)

            # Size: 15-18% of video width, cap at 180px
            max_logo_w = min(int(w * 0.18), 180)
            ratio = max_logo_w / img.width
            logo_h = int(img.height * ratio)
            img = img.resize((max_logo_w, logo_h), Image.LANCZOS)

            # Position: top-center with 5% padding — never overlaps captions
            logo_x = (w - max_logo_w) // 2
            logo_y = int(h * 0.05)

            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            overlay.paste(img, (logo_x, logo_y), img)

            path = job_dir / "char_overlay.png"
            overlay.save(str(path), "PNG")
            return str(path)
        except Exception as e:
            logger.warning(f"Character overlay failed: {e}")
            return None

    def _remove_background(self, img: Image.Image) -> Image.Image:
        """
        Auto-remove solid/uniform background from logo images.

        Strategy:
          1. Sample corner pixels to detect background color
          2. Make pixels matching the background transparent
          3. Add slight feathering at edges for smooth blend
        """
        w, h = img.size
        pixels = img.load()

        # Sample 4 corners to detect background color
        corners = [
            pixels[0, 0],
            pixels[w - 1, 0],
            pixels[0, h - 1],
            pixels[w - 1, h - 1],
        ]

        # Check if corners are similar (uniform background)
        def _color_dist(a, b):
            return sum(abs(a[i] - b[i]) for i in range(3))

        all_similar = all(
            _color_dist(corners[0], c) < 60 for c in corners[1:]
        )

        if not all_similar:
            # Already has transparency or complex background — skip
            # But still try: make near-white pixels transparent
            bg_r, bg_g, bg_b = corners[0][:3]
        else:
            bg_r, bg_g, bg_b = corners[0][:3]

        # Create new RGBA image with background removed
        new_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        new_pixels = new_img.load()

        threshold = 80  # Color distance threshold for background

        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                dist = abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b)

                if dist < threshold:
                    # Background pixel → make fully transparent
                    new_pixels[x, y] = (r, g, b, 0)
                elif dist < threshold + 40:
                    # Edge pixel → semi-transparent for smooth blend
                    alpha = int(255 * (dist - threshold) / 40)
                    new_pixels[x, y] = (r, g, b, alpha)
                else:
                    # Foreground pixel → keep as-is
                    new_pixels[x, y] = (r, g, b, a)

        return new_img

    # ── Main render ──

    def _render(self, script, voice_path, char_overlay, output_path,
                w, h, audio_dur, orientation, job_dir, pexels_key,
                script_ai_videos=None, script_ai_images=None, character_frames=None, niche=""):
        segments = self._build_segments(script, audio_dur)

        # Build AI video lookup: map segment index to video path
        ai_video_map = {}
        if script_ai_videos:
            ai_video_map = self._build_ai_video_map(segments, script_ai_videos)
            if ai_video_map:
                logger.info(f"🎬 {len(ai_video_map)}/{len(segments)} segments have AI video clips")

        # Build AI image lookup: map segment index to image path
        ai_image_map = {}
        if script_ai_images:
            ai_image_map = self._build_ai_image_map(segments, script_ai_images)
            if ai_image_map:
                logger.info(f"🎨 {len(ai_image_map)}/{len(segments)} segments have AI images")

        # Download stock footage (only for segments without AI images)
        stock_dir = job_dir / "stock_clips"
        stock_dir.mkdir(exist_ok=True)
        stock_clips = {}

        segments_needing_stock = [
            (idx, seg) for idx, seg in enumerate(segments)
            if idx not in ai_video_map  # AI video trumps stock
            and idx not in ai_image_map
        ]

        if pexels_key and segments_needing_stock:
            logger.info(f"Downloading stock footage for {len(segments_needing_stock)} segments...")
            for idx, seg in segments_needing_stock:
                clip = get_stock_for_scene(
                    seg["text"], seg.get("visual", ""), idx,
                    stock_dir, orientation, pexels_key,
                    target_duration=seg.get("duration"),
                    niche=niche,
                )
                if clip:
                    stock_clips[idx] = clip
            logger.info(f"Downloaded {len(stock_clips)}/{len(segments_needing_stock)} stock clips")

        # Render each segment
        temp_dir = job_dir / "temp_render"
        temp_dir.mkdir(exist_ok=True)
        video_segments = []
        segment_durations = []

        for idx, seg in enumerate(segments):
            seg_out = temp_dir / f"seg_{idx:03d}.mp4"
            dur = seg["duration"]
            char_frames = (character_frames or {}).get(str(idx), [])
            ai_clip = ai_video_map.get(idx)
            ai_img = ai_image_map.get(idx)
            stock = stock_clips.get(idx)

            ok = False

            # Determine character overlay for this segment
            # Use animated character frame if available, else static overlay
            seg_char_overlay = char_overlay
            if char_frames:
                # Use first character frame as overlay for this segment
                seg_char_overlay = char_frames[0]
                logger.debug(f"🎭 Animated character frame for segment {idx}")

            # Priority 0: AI-generated video clip (from Kling/Runway)
            if ai_clip and Path(ai_clip).exists():
                caption = create_caption_overlay(
                    seg["text"], w, h, seg["type"],
                    seg.get("num", 0), seg.get("total", 0),
                )
                cap_path = temp_dir / f"cap_{idx:03d}.png"
                caption.save(str(cap_path), "PNG")
                ok = create_stock_segment(
                    ai_clip, cap_path, seg_char_overlay,
                    seg_out, w, h, dur,
                )
                logger.debug(f"🎬 AI video clip used for segment {idx}")

            # Priority 1: AI-generated image (from Pixelle-Video)
            elif ai_img and Path(ai_img).exists():
                caption = create_caption_overlay(
                    seg["text"], w, h, seg["type"],
                    seg.get("num", 0), seg.get("total", 0),
                )
                cap_path = temp_dir / f"cap_{idx:03d}.png"
                caption.save(str(cap_path), "PNG")

                # Compose AI image as background with caption overlay
                ai_bg = self._compose_ai_background(ai_img, cap_path, seg_char_overlay, w, h)
                ai_bg_path = temp_dir / f"ai_frame_{idx:03d}.png"
                ai_bg.save(str(ai_bg_path), "PNG")
                ok = image_to_video_kenburns(ai_bg_path, seg_out, dur, w, h)

            # Priority 2: Pexels stock footage
            elif stock and stock.exists():
                caption = create_caption_overlay(
                    seg["text"], w, h, seg["type"],
                    seg.get("num", 0), seg.get("total", 0),
                )
                cap_path = temp_dir / f"cap_{idx:03d}.png"
                caption.save(str(cap_path), "PNG")
                ok = create_stock_segment(stock, cap_path, seg_char_overlay, seg_out, w, h, dur)

            # Priority 3: PIL gradient fallback
            if not ok:
                scene_colors = _get_scene_colors(script)
                bg = scene_colors[idx % len(scene_colors)]
                cs = script.get("color_scheme", {})
                accent = tuple(cs.get("accent", [124, 77, 255])[:3])
                frame = create_gradient_frame(
                    seg["text"], w, h, bg, seg["type"],
                    seg.get("num", 0), seg.get("total", 0), seg_char_overlay,
                    accent_color=accent,
                )
                frame_path = temp_dir / f"frame_{idx:03d}.png"
                frame.save(str(frame_path), "PNG")
                ok = image_to_video(frame_path, seg_out, dur)

            if ok and seg_out.exists():
                video_segments.append(str(seg_out))
                segment_durations.append(dur)
            else:
                if create_solid_segment(seg_out, w, h, dur):
                    video_segments.append(str(seg_out))
                    segment_durations.append(dur)

        if not video_segments:
            return False

        result = concat_with_xfade(
            video_segments, segment_durations, voice_path,
            output_path, temp_dir,
        )

        # Cleanup
        for f in temp_dir.glob("*"):
            f.unlink(missing_ok=True)
        temp_dir.rmdir()

        return result

    def _build_ai_video_map(self, segments: list, ai_videos: list) -> Dict[int, str]:
        """
        Map segment indices to AI video clip paths.
        AI videos match by type and scene_id, same as images.
        """
        vid_map = {}
        hook_vid = None
        cta_vid = None
        scene_vids = {}

        for vid_info in ai_videos:
            vid_type = vid_info.get("type", "scene")
            path = vid_info.get("path", "")
            if not path or not Path(path).exists():
                continue
            if vid_type == "hook":
                hook_vid = path
            elif vid_type == "cta":
                cta_vid = path
            else:
                scene_id = vid_info.get("scene_id", 0)
                scene_vids[scene_id] = path

        scene_counter = 0
        for idx, seg in enumerate(segments):
            seg_type = seg.get("type", "scene")
            if seg_type == "hook" and hook_vid:
                vid_map[idx] = hook_vid
            elif seg_type == "cta" and cta_vid:
                vid_map[idx] = cta_vid
            elif seg_type == "scene":
                scene_counter += 1
                if scene_counter in scene_vids:
                    vid_map[idx] = scene_vids[scene_counter]

        return vid_map

    def _build_ai_image_map(self, segments: list, ai_images: list) -> Dict[int, str]:
        """
        Map segment indices to AI image paths.
        AI images have types: hook, scene, cta — match them to segments.
        """
        img_map = {}

        # Build lookup by type and scene_id
        hook_img = None
        cta_img = None
        scene_imgs = {}  # scene_id -> path

        for img_info in ai_images:
            img_type = img_info.get("type", "scene")
            path = img_info.get("path", "")
            if not path or not Path(path).exists():
                continue
            if img_type == "hook":
                hook_img = path
            elif img_type == "cta":
                cta_img = path
            else:
                scene_id = img_info.get("scene_id", 0)
                scene_imgs[scene_id] = path

        scene_counter = 0
        for idx, seg in enumerate(segments):
            seg_type = seg.get("type", "scene")
            if seg_type == "hook" and hook_img:
                img_map[idx] = hook_img
            elif seg_type == "cta" and cta_img:
                img_map[idx] = cta_img
            elif seg_type == "scene":
                scene_counter += 1
                if scene_counter in scene_imgs:
                    img_map[idx] = scene_imgs[scene_counter]

        return img_map

    def _compose_ai_background(
        self, ai_img_path: str, caption_path: str,
        char_overlay: Optional[str], w: int, h: int
    ) -> Image.Image:
        """
        Compose an AI image as background with caption and character overlays.
        Uses light vignette instead of heavy dark overlay — lets AI image breathe.
        """
        # Load and resize AI image to fill frame
        bg = Image.open(ai_img_path).convert("RGBA")
        bg = bg.resize((w, h), Image.LANCZOS)

        # Subtle bottom gradient only (for text readability)
        # Much lighter than full-frame dark overlay
        gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        grad_draw = ImageDraw.Draw(gradient)
        # Bottom 40% gets a gentle gradient
        grad_start = int(h * 0.6)
        for y in range(grad_start, h):
            progress = (y - grad_start) / (h - grad_start)
            alpha = int(100 * progress)  # max 100 alpha, very gentle
            grad_draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        # Top 15% gets a subtle gradient for top UI elements
        for y in range(0, int(h * 0.15)):
            progress = 1 - (y / (h * 0.15))
            alpha = int(60 * progress)
            grad_draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        bg = Image.alpha_composite(bg, gradient)

        # Add caption
        if caption_path and Path(caption_path).exists():
            caption = Image.open(str(caption_path)).convert("RGBA")
            bg = Image.alpha_composite(bg, caption)

        # Add character
        if char_overlay and Path(char_overlay).exists():
            char = Image.open(char_overlay).convert("RGBA")
            bg = Image.alpha_composite(bg, char)

        return bg.convert("RGB")

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