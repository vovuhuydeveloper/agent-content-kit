"""
Stock Footage Service — Download stock video clips from Pexels API.
"""

import logging
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger("agent.composer.stock")

FALLBACK_SEARCHES = [
    "education classroom", "students learning", "technology digital",
    "school children", "colorful abstract", "creative design",
    "coding programming", "happy kids", "books library",
]


def download_stock_video(
    search_query: str,
    output_path: Path,
    api_key: str,
    orientation: str = "portrait",
) -> bool:
    """Download a stock video clip from Pexels API"""
    if not api_key:
        return False

    try:
        headers = {"Authorization": api_key}
        params = {
            "query": search_query,
            "orientation": orientation,
            "per_page": 5,
            "size": "medium",
        }
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers, params=params, timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(f"Pexels API error: {resp.status_code}")
            return False

        videos = resp.json().get("videos", [])
        if not videos:
            return False

        for video in videos:
            for vf in video.get("video_files", []):
                if vf.get("quality") in ["hd", "sd"] and vf.get("width", 0) >= 720:
                    r = requests.get(vf["link"], timeout=30, stream=True)
                    if r.status_code == 200:
                        with open(output_path, "wb") as f:
                            for chunk in r.iter_content(8192):
                                f.write(chunk)
                        logger.info(f"Stock video downloaded: {search_query}")
                        return True
        return False
    except Exception as e:
        logger.warning(f"Pexels download failed: {e}")
        return False


def _simplify_query(visual_hint: str, scene_text: str) -> str:
    """Extract 2-3 key words from visual hint for better Pexels search results"""
    # Remove common filler words from visual hints
    stop_words = {
        'footage', 'showing', 'visuals', 'of', 'the', 'a', 'an', 'in', 'on',
        'with', 'and', 'or', 'being', 'that', 'this', 'for', 'from', 'to',
        'is', 'are', 'was', 'were', 'it', 'its', 'their', 'our', 'user',
        'person', 'people', 'someone', 'display', 'screen', 'symbolizing',
        'showcasing', 'featuring', 'depicting', 'illustrating', 'split-screen',
    }

    text = visual_hint if visual_hint else scene_text
    words = [w.strip('.,!?"\'()') for w in text.lower().split()]
    keywords = [w for w in words if w and len(w) > 2 and w not in stop_words]

    # Take first 3 meaningful keywords
    return ' '.join(keywords[:3]) if keywords else 'technology digital'


def get_stock_for_scene(
    scene_text: str,
    visual_hint: str,
    scene_idx: int,
    output_dir: Path,
    orientation: str,
    api_key: str,
) -> Optional[Path]:
    """Get stock footage for a scene — try simplified query, then fallback"""
    output_path = output_dir / f"stock_{scene_idx}.mp4"
    orient = "portrait" if orientation == "vertical" else "landscape"

    query = _simplify_query(visual_hint, scene_text)
    logger.info(f"Stock search: '{query}' (from: '{visual_hint[:60]}')")

    if download_stock_video(query, output_path, api_key, orient):
        return output_path

    # Try broader fallback
    fallback = FALLBACK_SEARCHES[scene_idx % len(FALLBACK_SEARCHES)]
    logger.info(f"Stock fallback: '{fallback}'")
    if download_stock_video(fallback, output_path, api_key, orient):
        return output_path

    return None
