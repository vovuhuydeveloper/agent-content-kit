"""
CompetitorAnalyzerAgent — Analyze competitor content.
Fetches metadata and transcripts from competitor URLs using yt-dlp,
then uses LLM to analyze patterns and recommend strategies.
"""
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseAgent

logger = logging.getLogger("agent.analyzer")


class CompetitorAnalyzerAgent(BaseAgent):
    name = "CompetitorAnalyzerAgent"
    description = "Analyze competitor content for insights"
    is_critical = False  # Non-critical — pipeline continues if this fails

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        competitor_urls = context.get("competitor_urls", [])
        if not competitor_urls:
            self.skip("no competitor URLs")
            return {}

        logger.info(f"Analyzing {len(competitor_urls)} competitor URLs...")

        competitors_data = []
        for url in competitor_urls:
            try:
                data = self._fetch_competitor_data(url)
                if data:
                    competitors_data.append(data)
            except Exception as e:
                logger.warning(f"Failed to fetch competitor {url}: {e}")

        if not competitors_data:
            logger.warning("No competitor data retrieved")
            return {"competitor_insights": {"competitors_analyzed": 0}}

        # Analyze with LLM
        insights = self._analyze_with_llm(competitors_data, context)

        logger.info(
            f"Competitor analysis complete: {len(competitors_data)} analyzed, "
            f"{len(insights.get('common_hooks', []))} common hooks found"
        )

        return {"competitor_insights": insights}

    def _fetch_competitor_data(self, url: str) -> Dict[str, Any]:
        """Fetch metadata and transcript for a single competitor URL."""
        try:
            # Step 1: Get metadata via --dump-json
            cmd = [
                "yt-dlp", "--dump-json", "--no-download",
                "--no-playlist", "--flat-playlist",
                url,
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                logger.warning(f"yt-dlp metadata failed for {url}: {result.stderr[:200]}")
                return {}

            info = json.loads(result.stdout)
            data = {
                "url": url,
                "title": info.get("title", ""),
                "description": info.get("description", "")[:2000],
                "duration": info.get("duration", 0),
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
                "upload_date": info.get("upload_date", ""),
                "tags": info.get("tags", []) or [],
                "categories": info.get("categories", []) or [],
                "transcript": "",
            }

            # Step 2: Try to get transcript
            data["transcript"] = self._fetch_transcript(url)

            return data

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout fetching {url}")
            return {}
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from yt-dlp for {url}: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Competitor fetch failed for {url}: {e}")
            return {}

    def _fetch_transcript(self, url: str) -> str:
        """Fetch subtitles/transcript using yt-dlp."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                cmd = [
                    "yt-dlp",
                    "--write-subs", "--write-auto-subs",
                    "--sub-lang", "en,vi,en-US,en-GB",
                    "--skip-download",
                    "--convert-subs", "srt",
                    "--output", f"{tmpdir}/%(id)s",
                    url,
                ]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30
                )

                # Find any subtitle files
                tmp = Path(tmpdir)
                sub_files = list(tmp.rglob("*.srt")) + list(tmp.rglob("*.vtt"))
                if sub_files:
                    content = sub_files[0].read_text(encoding="utf-8", errors="ignore")
                    return self._extract_text_from_subtitles(content)

                return ""
        except Exception as e:
            logger.debug(f"Transcript fetch failed for {url}: {e}")
            return ""

    @staticmethod
    def _extract_text_from_subtitles(raw: str) -> str:
        """Strip SRT/VTT timestamps and index numbers, return plain text."""
        lines = []
        for line in raw.split("\n"):
            line = line.strip()
            # Skip index numbers, timestamps, and WEBVTT header lines
            if not line:
                continue
            if line.isdigit():
                continue
            if "-->" in line:
                continue
            if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            if line.startswith("<") and line.endswith(">"):
                continue
            lines.append(line)
        return " ".join(lines)[:3000]

    def _analyze_with_llm(
        self, competitors_data: List[Dict], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to extract patterns and insights from competitor data."""
        niche = context.get("niche", "")
        language = context.get("language", "vi")

        # Build a compact summary for the LLM prompt
        summaries = []
        for i, comp in enumerate(competitors_data[:10]):
            summaries.append(
                f"Video {i + 1}: \"{comp['title']}\"\n"
                f"  Views: {comp.get('view_count', 0):,} | Likes: {comp.get('like_count', 0):,}\n"
                f"  Duration: {comp.get('duration', 0)}s | Tags: {', '.join(comp.get('tags', [])[:5])}\n"
                f"  Description: {comp.get('description', '')[:300]}\n"
                f"  Transcript excerpt: {comp.get('transcript', '')[:500]}\n"
            )

        prompt = (
            f"Analyze these {len(competitors_data)} competitor videos "
            f"in the niche '{niche}' (language: {language}).\n\n"
            + "\n".join(summaries)
            + "\n\nBased on the data above, identify:\n"
            "1. Common hook patterns (how they grab attention)\n"
            "2. Content structures (how they organize the video)\n"
            "3. Trending hashtags or topics\n"
            "4. Engagement patterns (what drives likes/views)\n"
            "5. Differentiation opportunities (what gaps exist)\n\n"
            "Return a JSON object with keys: common_hooks (list[str]), "
            "content_structures (list[str]), trending_hashtags (list[str]), "
            "engagement_patterns (list[str]), differentiation_opportunities (list[str])."
        )

        try:
            from .llm_client import get_llm_client

            llm = get_llm_client()
            result = llm.generate_json(prompt)
            result["competitors_analyzed"] = len(competitors_data)
            return result
        except Exception as e:
            logger.warning(f"LLM analysis failed, using basic heuristics: {e}")
            return self._fallback_analysis(competitors_data)

    def _fallback_analysis(self, competitors_data: List[Dict]) -> Dict[str, Any]:
        """Basic heuristic analysis when LLM is unavailable."""
        all_tags = []
        for comp in competitors_data:
            all_tags.extend(comp.get("tags", []))

        # Count tag frequency
        tag_freq = {}
        for tag in all_tags:
            tag_freq[tag] = tag_freq.get(tag, 0) + 1

        top_tags = sorted(tag_freq, key=tag_freq.get, reverse=True)[:10]

        return {
            "competitors_analyzed": len(competitors_data),
            "common_hooks": ["Question-based openings", "Shocking facts"],
            "content_structures": ["Problem → Solution", "Listicle format"],
            "trending_hashtags": top_tags if top_tags else ["#trending"],
            "engagement_patterns": [
                "Higher engagement on shorter videos (<60s)",
                "Questions in captions drive comments",
            ],
            "differentiation_opportunities": [
                "Focus on underserved sub-niche angles",
                "Add personal storytelling to stand out",
            ],
        }
