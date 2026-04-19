"""
ContentFetcherAgent — Fetch web content via BeautifulSoup / yt-dlp.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

import requests
from bs4 import BeautifulSoup

from .base import BaseAgent

logger = logging.getLogger("agent.fetcher")


class ContentFetcherAgent(BaseAgent):
    name = "ContentFetcherAgent"
    description = "Fetch and parse web/video content"
    is_critical = True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        url = context["source_url"]
        job_dir = Path(context["job_dir"])
        source_type = context.get("source_type", "")

        # Document upload — parse local file
        if source_type == "document" or context.get("source_document_path"):
            doc_path = context.get("source_document_path", url)
            content_data = self._fetch_document(doc_path)
        elif any(d in url for d in ["youtube.com", "youtu.be", "tiktok.com"]):
            content_data = self._fetch_video(url)
        elif "apps.apple.com" in url or "itunes.apple.com" in url:
            content_data = self._fetch_appstore(url)
        elif "play.google.com" in url:
            content_data = self._fetch_webpage(url)
        else:
            content_data = self._fetch_webpage(url)

        # Save
        out_path = job_dir / "content_data.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(content_data, f, ensure_ascii=False, indent=2)

        return {"content_data": content_data}

    def _fetch_document(self, file_path: str) -> Dict:
        """Parse uploaded document (PDF/DOCX/TXT)"""
        try:
            from .document_parser import parse_document
            return parse_document(file_path)
        except Exception as e:
            logger.error(f"Document parsing failed: {e}")
            return {
                "source_url": file_path, "source_type": "document",
                "title": Path(file_path).stem, "description": "",
                "body_text": f"Parse error: {e}", "transcript": "",
                "metadata": {},
            }

    def _fetch_appstore(self, url: str) -> Dict:
        """Fetch app info from Apple App Store via iTunes Lookup API"""
        import re
        try:
            # Extract app ID from URL: .../id6753631200
            match = re.search(r'/id(\d+)', url)
            if not match:
                logger.warning(f"Cannot extract App ID from {url}, falling back to webpage")
                return self._fetch_webpage(url)

            app_id = match.group(1)
            # Use iTunes Lookup API (free, no auth needed)
            lookup_url = f"https://itunes.apple.com/lookup?id={app_id}&country=us"
            r = requests.get(lookup_url, timeout=15)
            r.raise_for_status()
            data = r.json()

            if data.get("resultCount", 0) == 0:
                # Try Vietnamese store
                lookup_url = f"https://itunes.apple.com/lookup?id={app_id}&country=vn"
                r = requests.get(lookup_url, timeout=15)
                data = r.json()

            if data.get("resultCount", 0) == 0:
                return self._fetch_webpage(url)

            app = data["results"][0]
            app_name = app.get("trackName", "")
            description = app.get("description", "")
            short_desc = app.get("releaseNotes", "")
            price = app.get('price', 0)
            price_str = 'Free' if price == 0 else f'${price}'
            rating = app.get('averageUserRating', 0) or 0
            rating_count = app.get('userRatingCount', 0)

            # Build rich content for script generation
            body_parts = [
                f"App Name: {app_name}",
                f"Developer: {app.get('artistName', '')}",
                f"Category: {app.get('primaryGenreName', '')}",
                f"Price: {price_str}",
                f"Rating: {rating:.1f}/5 ({rating_count} reviews)",
                "",
                "Description:",
                description[:3000],
                "",
                "What's New:",
                short_desc[:500] if short_desc else "N/A",
                "",
                f"Supported Devices: {', '.join(app.get('supportedDevices', [])[:5])}",
                f"Languages: {', '.join(app.get('languageCodesISO2A', [])[:10])}",
            ]

            logger.info(f"App Store: {app_name} — {len(description)} chars description")

            return {
                "source_url": url, "source_type": "appstore",
                "title": app_name,
                "description": description[:500],
                "body_text": "\n".join(body_parts),
                "content": "\n".join(body_parts),
                "transcript": "",
                "metadata": {
                    "app_id": app_id,
                    "developer": app.get("artistName", ""),
                    "rating": app.get("averageUserRating"),
                    "rating_count": app.get("userRatingCount"),
                    "icon_url": app.get("artworkUrl512", ""),
                    "screenshots": app.get("screenshotUrls", [])[:5],
                    "category": app.get("primaryGenreName", ""),
                },
            }
        except Exception as e:
            logger.error(f"App Store fetch failed: {e}")
            return self._fetch_webpage(url)

    def _fetch_webpage(self, url: str) -> Dict:
        try:
            r = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; AgentContentKit/1.0)"
            })
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            desc_tag = soup.find("meta", attrs={"name": "description"})
            description = desc_tag["content"] if desc_tag and desc_tag.get("content") else ""
            body_text = soup.get_text(separator="\n", strip=True)[:8000]

            return {
                "source_url": url, "source_type": "webpage",
                "title": title, "description": description,
                "body_text": body_text, "transcript": "", "metadata": {},
            }
        except Exception as e:
            logger.error(f"Webpage fetch failed: {e}")
            return {
                "source_url": url, "source_type": "webpage",
                "title": url, "description": "", "body_text": str(e),
                "transcript": "", "metadata": {},
            }

    def _fetch_video(self, url: str) -> Dict:
        try:
            cmd = ["yt-dlp", "--dump-json", "--no-download", url]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                info = json.loads(r.stdout)
                return {
                    "source_url": url, "source_type": "youtube",
                    "title": info.get("title", ""),
                    "description": info.get("description", "")[:5000],
                    "body_text": info.get("description", ""),
                    "transcript": "", "metadata": {
                        "duration": info.get("duration"),
                        "view_count": info.get("view_count"),
                    },
                }
        except Exception as e:
            logger.warning(f"yt-dlp failed: {e}")

        return {
            "source_url": url, "source_type": "video",
            "title": url, "description": "", "body_text": "",
            "transcript": "", "metadata": {},
        }
