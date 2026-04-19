"""
TikTok Trend Scraper — Fetch trending hashtags & sounds from TikTok Creative Center.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import requests

from .base import BaseAgent

logger = logging.getLogger("agent.trend_scraper")

# TikTok Creative Center API (public, no auth needed)
CREATIVE_CENTER_API = "https://ads.tiktok.com/creative_radar_api/v1/popular"


class TrendScraperAgent(BaseAgent):
    name = "TrendScraperAgent"
    description = "Fetch trending hashtags & sounds from TikTok Creative Center"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        niche = context.get("niche", "")
        language = context.get("language", "vi")
        job_dir = Path(context["job_dir"])

        country = "VN" if language == "vi" else "US"

        trends = {
            "hashtags": self._fetch_trending_hashtags(country, niche),
            "sounds": self._fetch_trending_sounds(country),
        }

        # Save trends
        trends_path = job_dir / "trends.json"
        with open(trends_path, "w", encoding="utf-8") as f:
            json.dump(trends, f, ensure_ascii=False, indent=2)

        logger.info(f"Fetched {len(trends['hashtags'])} hashtags, {len(trends['sounds'])} sounds")
        return {
            "trends": trends,
            "trends_path": str(trends_path),
        }

    def _fetch_trending_hashtags(self, country: str, niche: str) -> List[Dict]:
        """Fetch trending hashtags from TikTok Creative Center"""
        try:
            resp = requests.get(
                f"{CREATIVE_CENTER_API}/hashtag/list/",
                params={
                    "page": 1,
                    "limit": 20,
                    "period": 7,  # last 7 days
                    "country_code": country,
                    "sort_by": "popular",
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                    "Accept": "application/json",
                },
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("list", [])
                hashtags = []
                for item in items[:15]:
                    hashtags.append({
                        "name": item.get("hashtag_name", ""),
                        "views": item.get("video_views", 0),
                        "posts": item.get("publish_cnt", 0),
                        "trend": item.get("trend", 0),  # 1=rising, -1=declining
                    })
                return hashtags
            else:
                logger.warning(f"TikTok hashtag API returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"TikTok hashtag fetch failed: {e}")

        # Fallback: return generic trending hashtags
        return self._fallback_hashtags(niche)

    def _fetch_trending_sounds(self, country: str) -> List[Dict]:
        """Fetch trending sounds/music from TikTok"""
        try:
            resp = requests.get(
                f"{CREATIVE_CENTER_API}/music/list/",
                params={
                    "page": 1,
                    "limit": 10,
                    "period": 7,
                    "country_code": country,
                    "sort_by": "popular",
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                    "Accept": "application/json",
                },
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("list", [])
                sounds = []
                for item in items[:10]:
                    sounds.append({
                        "title": item.get("title", ""),
                        "author": item.get("author", ""),
                        "usage_count": item.get("video_cnt", 0),
                    })
                return sounds
        except Exception as e:
            logger.warning(f"TikTok sounds fetch failed: {e}")

        return []

    def _fallback_hashtags(self, niche: str) -> List[Dict]:
        """Fallback hashtags when API fails"""
        base = [
            {"name": "fyp", "views": 0, "posts": 0, "trend": 1},
            {"name": "viral", "views": 0, "posts": 0, "trend": 1},
            {"name": "trending", "views": 0, "posts": 0, "trend": 1},
        ]
        if niche:
            base.insert(0, {"name": niche.replace(" ", ""), "views": 0, "posts": 0, "trend": 1})
        return base
