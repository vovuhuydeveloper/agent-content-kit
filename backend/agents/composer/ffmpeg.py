"""
FFmpeg Service — Video segment creation, concatenation, audio merge.

Enhanced: Ken Burns slow zoom, crossfade transitions, audio-synced rendering.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("agent.composer.ffmpeg")

# ── Audio ──

def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds"""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip())
    except Exception:
        return 45.0


# ── Image → Video segments ──

def image_to_video(
    image_path: Path,
    output_path: Path,
    duration: float,
    timeout: int = 120,
) -> bool:
    """Convert a still image to a video segment (static, no movement)"""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-c:v", "libx264", "-t", f"{duration:.2f}",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-preset", "ultrafast",
        str(output_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode == 0


def image_to_video_kenburns(
    image_path: Path,
    output_path: Path,
    duration: float,
    w: int = 1080,
    h: int = 1920,
    zoom_speed: float = 0.0015,
    max_zoom: float = 1.08,
    timeout: int = 180,
) -> bool:
    """
    Convert a still image to video with Ken Burns slow zoom effect.

    Applies a subtle continuous zoom-in that makes static AI images
    feel dynamic and engaging — essential for TikTok/Shorts format.

    Args:
        zoom_speed: Zoom increment per frame (0.0015 = gentle)
        max_zoom: Maximum zoom level (1.08 = 8% zoom over duration)

    FFmpeg zoompan math:
        z = current zoom level, incremented each frame
        x,y = pan offset to keep image centered during zoom
    """
    # Number of frames
    fps = 30

    # Build zoompan expression
    # zoom starts at 1.0, increases by zoom_speed each frame, capped at max_zoom
    zoom_expr = f"min(zoom+{zoom_speed},{max_zoom})"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-vf",
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"zoompan=z='{zoom_expr}':d=1:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={w}x{h}:fps={fps}",
        "-c:v", "libx264",
        "-t", f"{duration:.2f}",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        str(output_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    if r.returncode == 0:
        return True

    # Fallback: static image without zoom
    logger.warning(
        f"Ken Burns zoom failed for {image_path.name} — "
        f"falling back to static image"
    )
    return image_to_video(image_path, output_path, duration, timeout)


def create_stock_segment(
    stock_path: Path,
    caption_frames: Optional[List[Path]],
    char_overlay: Optional[str],
    output: Path,
    w: int,
    h: int,
    duration: float,
    timeout: int = 120,
) -> bool:
    """
    Create segment from stock footage with optional zoom + caption + character.

    If caption_frames is provided (list of per-second caption PNGs),
    overlays them sequentially for audio-synced caption effect.
    """
    inputs = ["-i", str(stock_path)]

    # Build filter complex with color grading
    filter_parts = [
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
        f"zoompan=z='min(zoom+0.001,1.04)':d=1:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={w}x{h}:fps=30,"
        # Color grade: boost contrast, saturation, slight vignette for TikTok look
        f"eq=contrast=1.15:brightness=0.02:saturation=1.2,"
        f"vignette=PI/4:max_even:half_face[bg]",
    ]

    # Audio-synced caption frames
    if caption_frames and len(caption_frames) > 0:
        for i, cap_path in enumerate(caption_frames):
            inputs.extend(["-i", str(cap_path)])
            src_label = "[bg]" if i == 0 else f"[cap{i - 1}]"
            filter_parts.append(
                f"{src_label}[{i + 1}:v]overlay=0:0[cap{i}]"
            )
        overlay_label = f"[cap{len(caption_frames) - 1}]"
    else:
        overlay_label = "[bg]"

    # Character overlay
    if char_overlay and os.path.exists(char_overlay):
        inputs.extend(["-i", str(char_overlay)])
        filter_parts.append(
            f"{overlay_label}[{len(inputs) - 1}:v]overlay=0:0[out]"
        )
        map_out = "[out]"
    else:
        map_out = overlay_label

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", map_out,
        "-c:v", "libx264", "-preset", "ultrafast",
        "-t", f"{duration:.2f}", "-r", "30",
        "-pix_fmt", "yuv420p",
        str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    if r.returncode == 0:
        return True

    # Fallback: simple overlay without zoom
    logger.warning("Stock segment with effects failed — using simple overlay")
    return _create_stock_segment_simple(
        stock_path, caption_frames[0] if caption_frames else None,
        char_overlay, output, w, h, duration, timeout,
    )


def _create_stock_segment_simple(
    stock_path: Path,
    caption_path: Optional[Path],
    char_overlay: Optional[str],
    output: Path,
    w: int,
    h: int,
    duration: float,
    timeout: int = 120,
) -> bool:
    """Simplified stock segment without effects"""
    inputs = ["-i", str(stock_path)]
    filter_parts = [
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[bg]",
    ]

    next_idx = 1
    if caption_path and caption_path.exists():
        inputs.extend(["-i", str(caption_path)])
        filter_parts.append(f"[bg][{next_idx}:v]overlay=0:0[captioned]")
        next_idx += 1
        base = "[captioned]"
    else:
        base = "[bg]"

    if char_overlay and os.path.exists(char_overlay):
        inputs.extend(["-i", str(char_overlay)])
        filter_parts.append(f"{base}[{next_idx}:v]overlay=0:0[out]")
        map_out = "[out]"
    else:
        map_out = base

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", map_out,
        "-c:v", "libx264", "-preset", "ultrafast",
        "-t", f"{duration:.2f}", "-r", "30",
        "-pix_fmt", "yuv420p",
        str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode == 0


def create_solid_segment(
    output: Path, w: int, h: int, duration: float
) -> bool:
    """Ultra minimal fallback — solid color video"""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=#1a0a3e:s={w}x{h}:d={duration:.2f}:r=30",
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
        str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return r.returncode == 0


# ── Concatenation ──

def concat_with_audio(
    segment_files: List[str],
    audio_path: Path,
    output_path: Path,
    temp_dir: Path,
    timeout: int = 300,
) -> bool:
    """Concatenate video segments with audio (no transitions)"""
    concat_list = temp_dir / "concat.txt"
    with open(concat_list, "w") as f:
        for sf in segment_files:
            f.write(f"file '{os.path.abspath(sf)}'\n")

    logger.info(f"Concatenating {len(segment_files)} segments + audio")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(output_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    if r.returncode == 0:
        return True
    logger.error(f"Concat failed: {r.stderr[-500:]}")
    return False


def concat_with_xfade(
    segment_files: List[str],
    segment_durations: List[float],
    audio_path: Path,
    output_path: Path,
    temp_dir: Path,
    xfade_duration: float = 0.35,
    timeout: int = 600,
) -> bool:
    """
    Concatenate video segments with smooth crossfade transitions.

    Uses ffmpeg xfade filter for professional transitions between scenes.
    Falls back to simple concat if xfade is not supported.

    Args:
        segment_files: List of segment video file paths
        segment_durations: Duration of each segment in seconds
        xfade_duration: Crossfade transition duration (0.2–0.5s recommended)
    """
    if len(segment_files) < 2:
        # Single segment — simple concat
        return concat_with_audio(
            segment_files, audio_path, output_path, temp_dir, timeout
        )

    logger.info(
        f"Concatenating {len(segment_files)} segments "
        f"with {xfade_duration}s xfade transitions"
    )

    # Build ffmpeg command with multiple inputs + xfade chain
    cmd = ["ffmpeg", "-y"]

    # Add all segment inputs
    for sf in segment_files:
        cmd.extend(["-i", str(sf)])

    # Build xfade filter chain
    # For N segments with crossfade of duration D:
    #   Total output = sum(durations) - (N-1) * D
    total_duration = sum(segment_durations) - (len(segment_files) - 1) * xfade_duration

    filter_parts = []
    current_offset = 0

    for i in range(len(segment_files) - 1):
        offset = segment_durations[i] - xfade_duration + current_offset
        if i == 0:
            filter_parts.append(
                f"[0][1]xfade=transition=fade:duration={xfade_duration:.2f}:"
                f"offset={offset:.2f}[xf0]"
            )
        else:
            filter_parts.append(
                f"[xf{i - 1}][{i + 1}]xfade=transition=fade:duration={xfade_duration:.2f}:"
                f"offset={offset:.2f}[xf{i}]"
            )
        current_offset = offset

    last_xf = f"[xf{len(segment_files) - 2}]"

    # Add audio as input (before filter_complex for correct indexing)
    audio_input_idx = len(segment_files)
    cmd.extend(["-i", str(audio_path)])

    # Build filter + map
    filter_str = ";".join(filter_parts)
    cmd.extend([
        "-filter_complex", filter_str,
        "-map", last_xf,
        "-map", f"{audio_input_idx}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(output_path),
    ])

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    if r.returncode == 0:
        logger.info(
            f"✅ Xfade concat done: {len(segment_files)} segments, "
            f"total {total_duration:.1f}s"
        )
        return True

    # Fallback: simple concat
    logger.warning(
        f"Xfade failed (ffmpeg may be too old) — using simple concat. "
        f"Error: {r.stderr[-300:]}"
    )
    return concat_with_audio(
        segment_files, audio_path, output_path, temp_dir, timeout
    )
