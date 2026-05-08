"""
Stock Footage Service — Download stock video clips from Pexels API.

Enhanced: smart keyword extraction, quality scoring, duration matching,
dynamic fallback based on scene content.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger("agent.composer.stock")

# Generic fallback when no keywords extracted — diverse enough for any niche
GENERIC_FALLBACKS = [
    "technology digital abstract",
    "creative design colorful",
    "nature landscape aerial",
    "city urban modern",
    "education learning classroom",
    "business office corporate",
    "lifestyle trending viral",
    "art animation motion",
    "music dance rhythm",
    "science innovation future",
    "travel adventure explore",
    "food cooking cuisine",
    "fitness workout exercise",
    "fashion style beauty",
    "gaming esports stream",
]


def _extract_keywords(
    visual_hint: str, scene_text: str, max_keywords: int = 4
) -> list[str]:
    """
    Extract meaningful keywords from visual hint + scene text.

    Uses NLP-style heuristics: removes stop words, filters by minimum
    length, deduplicates while preserving order.
    """
    stop_words = {
        "footage", "showing", "visuals", "of", "the", "a", "an", "in", "on",
        "with", "and", "or", "being", "that", "this", "for", "from", "to",
        "is", "are", "was", "were", "it", "its", "their", "our", "user",
        "person", "people", "someone", "display", "screen", "symbolizing",
        "showcasing", "featuring", "depicting", "illustrating", "split-screen",
        "video", "clip", "scene", "shows", "has", "can", "will", "would",
        "should", "could", "may", "also", "like", "just", "very", "really",
        "actually", "basically", "literally", "definitely", "probably",
    }

    text = (visual_hint + " " + scene_text).lower()

    words = [w.strip('.,!?"\'()[]{}:;') for w in text.split()]
    keywords = [w for w in words if w and len(w) > 2 and w not in stop_words]

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return unique[:max_keywords]


def _build_queries(keywords: list[str]) -> list[str]:
    """
    Build multiple search query variants from keywords.

    Tries: full combo → pairs → individual with suffix.
    """
    queries: list[str] = []

    if keywords:
        queries.append(" ".join(keywords))

    # Pairs
    for i in range(len(keywords)):
        for j in range(i + 1, len(keywords)):
            queries.append(f"{keywords[i]} {keywords[j]}")

    # Individual with "background"/"footage" suffix
    for kw in keywords[:3]:
        queries.append(f"{kw} background")

    return queries


def _score_video(
    video: dict,
    search_query: str,
    target_duration: Optional[float] = None,
) -> float:
    """
    Score a Pexels video result for relevance and quality.

    Scoring factors:
      - Duration match (if target specified)
      - Resolution / HD quality
      - Duration in reasonable range for short-form (3–60s)
    """
    score = 0.0

    # Quality: prefer HD
    video_files = video.get("video_files", [])
    has_hd = any(
        vf.get("quality") == "hd" and vf.get("width", 0) >= 720
        for vf in video_files
    )
    if has_hd:
        score += 3.0

    # Resolution bonus
    max_width = max((vf.get("width", 0) for vf in video_files), default=0)
    if max_width >= 1920:
        score += 2.0
    elif max_width >= 1080:
        score += 1.0

    # Duration: prefer 5–30s for short-form content
    duration = video.get("duration", 0)
    if target_duration:
        diff = abs(duration - target_duration)
        if diff < 2:
            score += 5.0
        elif diff < 5:
            score += 3.0
        elif diff < 10:
            score += 1.0
    else:
        if 5 <= duration <= 30:
            score += 2.0
        elif 3 <= duration <= 60:
            score += 1.0

    return score


def download_stock_video(
    search_query: str,
    output_path: Path,
    api_key: str,
    orientation: str = "portrait",
    target_duration: Optional[float] = None,
    per_page: int = 20,
) -> bool:
    """
    Download the best-matching stock video clip from Pexels API.

    Enhanced: fetches more results, scores by quality + duration,
    picks the highest-scoring video.
    """
    if not api_key:
        return False

    try:
        headers = {"Authorization": api_key}
        params = {
            "query": search_query,
            "orientation": orientation,
            "per_page": min(per_page, 80),
            "size": "medium",
        }
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(f"Pexels API error: {resp.status_code}")
            return False

        videos = resp.json().get("videos", [])
        if not videos:
            return False

        # Score and sort videos
        scored = [
            (v, _score_video(v, search_query, target_duration)) for v in videos
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            f"Pexels found {len(videos)} videos for '{search_query}', "
            f"top score: {scored[0][1]:.1f}"
        )

        # Try videos in score order
        for video, score in scored:
            if score < 1.0:
                continue

            for vf in video.get("video_files", []):
                if vf.get("quality") in ("hd", "sd") and vf.get("width", 0) >= 720:
                    r = requests.get(vf["link"], timeout=30, stream=True)
                    if r.status_code == 200:
                        with open(output_path, "wb") as f:
                            for chunk in r.iter_content(8192):
                                f.write(chunk)
                        logger.info(
                            f"Stock video downloaded: '{search_query}' "
                            f"(score={score:.1f}, dur={video.get('duration', 0)}s)"
                        )
                        return True
        return False
    except Exception as e:
        logger.warning(f"Pexels download failed: {e}")
        return False


def _get_dynamic_fallback(
    visual_hint: str, scene_text: str, niche: str = ""
) -> str:
    """
    Generate dynamic fallback queries based on scene content.

    Much better than hardcoded generic terms — uses extracted keywords
    or niche to produce relevant search.
    """
    keywords = _extract_keywords(visual_hint, scene_text, max_keywords=3)

    if keywords:
        return " ".join(keywords)

    if niche:
        return f"{niche} content"

    # Deterministic fallback based on scene text hash
    idx = int(hashlib.md5(scene_text.encode()).hexdigest(), 16) % len(
        GENERIC_FALLBACKS
    )
    return GENERIC_FALLBACKS[idx]


def get_stock_for_scene(
    scene_text: str,
    visual_hint: str,
    scene_idx: int,
    output_dir: Path,
    orientation: str,
    api_key: str,
    target_duration: Optional[float] = None,
    niche: str = "",
) -> Optional[Path]:
    """
    Get stock footage for a scene — multi-query search with quality scoring.

    Strategy:
      1. Build multiple query variants from keywords.
      2. Try each query, score results, pick the best.
      3. Dynamic fallback based on scene content.
      4. Last resort: generic fallbacks.
    """
    output_path = output_dir / f"stock_{scene_idx}.mp4"
    orient = "portrait" if orientation == "vertical" else "landscape"

    # Extract keywords and build queries
    keywords = _extract_keywords(visual_hint, scene_text)
    queries = _build_queries(keywords)

    # Try each query
    for query in queries:
        logger.debug(f"Stock search: '{query}' (from: '{visual_hint[:60]}')")
        if download_stock_video(
            query,
            output_path,
            api_key,
            orient,
            target_duration=target_duration,
        ):
            return output_path

    # Dynamic fallback — based on actual scene content
    fallback = _get_dynamic_fallback(visual_hint, scene_text, niche)
    logger.info(f"Stock fallback (dynamic): '{fallback}'")
    if download_stock_video(
        fallback,
        output_path,
        api_key,
        orient,
        target_duration=target_duration,
    ):
        return output_path

    # Final fallback — generic
    for fb in GENERIC_FALLBACKS[:3]:
        if download_stock_video(fb, output_path, api_key, orient):
            return output_path

    return None
