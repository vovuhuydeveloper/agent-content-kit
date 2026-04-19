"""
FFmpeg Service — Video segment creation, concatenation, audio merge.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("agent.composer.ffmpeg")


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds"""
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip())
    except Exception:
        return 45.0


def image_to_video(image_path: Path, output_path: Path, duration: float, timeout: int = 120) -> bool:
    """Convert a still image to a video segment"""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-c:v", "libx264", "-t", f"{duration:.2f}",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-preset", "ultrafast",
        str(output_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode == 0


def create_stock_segment(
    stock_path: Path, caption_path: Path, char_overlay: Optional[str],
    output: Path, w: int, h: int, duration: float, timeout: int = 120,
) -> bool:
    """Create segment: stock footage + slow zoom + caption overlay + character"""
    inputs = ["-i", str(stock_path), "-i", str(caption_path)]
    filter_parts = [
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[bg]",
        "[bg][1:v]overlay=0:0[captioned]",
    ]

    if char_overlay and os.path.exists(char_overlay):
        inputs.extend(["-i", str(char_overlay)])
        filter_parts.append("[captioned][2:v]overlay=0:0[out]")
        map_out = "[out]"
    else:
        map_out = "[captioned]"

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
    if r.returncode != 0:
        # Fallback without zoompan
        filter_simple = [
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[bg]",
            "[bg][1:v]overlay=0:0[captioned]",
        ]
        if char_overlay and os.path.exists(char_overlay):
            filter_simple.append("[captioned][2:v]overlay=0:0[out]")
        cmd_fb = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", ";".join(filter_simple),
            "-map", map_out,
            "-c:v", "libx264", "-preset", "ultrafast",
            "-t", f"{duration:.2f}", "-r", "30",
            "-pix_fmt", "yuv420p",
            str(output),
        ]
        r = subprocess.run(cmd_fb, capture_output=True, text=True, timeout=timeout)
    return r.returncode == 0


def create_solid_segment(output: Path, w: int, h: int, duration: float) -> bool:
    """Ultra minimal fallback — solid color video"""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#1a0a3e:s={w}x{h}:d={duration:.2f}:r=30",
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
        str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return r.returncode == 0


def concat_with_audio(
    segment_files: List[str], audio_path: Path, output_path: Path,
    temp_dir: Path, timeout: int = 300,
) -> bool:
    """Concatenate video segments and add audio"""
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
