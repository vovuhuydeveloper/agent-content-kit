"""
ScriptWriterAgent — Generate video scripts via LLM.
Enhanced with TikTok trends, content uniqueness, and competitor analysis.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseAgent
from .llm_client import get_llm_client

logger = logging.getLogger("agent.scriptwriter")

# History file to track generated titles and avoid duplicates
HISTORY_FILE = Path("data/script_history.json")

SCRIPT_PROMPT = """You are an expert short-form video scriptwriter for TikTok/YouTube Shorts.
Create {video_count} UNIQUE video scripts to promote the app/product below.

=== APP / PRODUCT INFO ===
{content}

{competitor_section}

{trend_section}

{history_section}

=== REQUIREMENTS ===
- Language: {language_name}
- Each script should be 30-60 seconds when spoken
- Format: Hook (3s) → Main Content (25-50s) → CTA (5s)
- CRITICAL: Each script must have a DIFFERENT angle/approach:
  * Script 1: Feature highlight / Demo
  * Script 2: Problem → Solution
  * Script 3: User testimonial / Social proof
  * Script 4: Before vs After
  * Script 5: Trending challenge / Hook style
  (pick the best {video_count} angles from above)
- Use a friendly character/mascot as the presenter
- Include trending hashtags from the trend data if available
- Call to action: download the app / try it now
- Tone: friendly, enthusiastic, authentic (not salesy)
{niche_hint}

=== OUTPUT FORMAT ===
Return a JSON array of scripts:
[
  {{
    "script_id": 1,
    "title": "Video title (catchy, SEO-friendly, UNIQUE)",
    "angle": "feature_demo|problem_solution|testimonial|before_after|trending",
    "hook": "Opening hook text (attention-grabbing, 1-2 sentences)",
    "scenes": [
      {{
        "scene_id": 1,
        "text": "What the presenter says in this scene",
        "duration": 5,
        "visual": "Description of background visual/footage needed",
        "character_pose": "standing|explaining|teaching|waving|questioning|celebrating"
      }}
    ],
    "cta": "Call to action text",
    "hashtags": ["relevant", "trending", "hashtags"],
    "estimated_duration": 45,
    "mood": "energetic|calm|professional|fun|dramatic|inspiring",
    "color_scheme": {{
      "primary": [R, G, B],
      "secondary": [R, G, B],
      "accent": [R, G, B]
    }}
  }}
]

IMPORTANT:
- Do NOT repeat angles, titles, or hooks from the history section
- Each script must offer genuinely different value to the viewer
- Use color_scheme matching the content mood
- Return ONLY valid JSON, no markdown
"""


class ScriptWriterAgent(BaseAgent):
    name = "ScriptWriterAgent"
    description = "Generate unique video scripts via LLM with trend integration"
    is_critical = True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        content_data = context["content_data"]
        video_count = context.get("video_count", 1)
        language = context.get("language", "vi")
        job_dir = Path(context["job_dir"])
        niche = context.get("niche", "")
        competitor_insights = context.get("competitor_insights")
        trends = context.get("trends")

        content = self._extract_text(content_data)
        language_name = "Vietnamese (tiếng Việt)" if language == "vi" else "English"

        # Competitor section
        competitor_section = ""
        if competitor_insights and isinstance(competitor_insights, dict):
            competitor_section = f"""
=== COMPETITOR ANALYSIS ===
Use these insights to DIFFERENTIATE our content:
{json.dumps(competitor_insights, ensure_ascii=False, indent=2)[:1500]}
"""

        # Trends section
        trend_section = ""
        if trends:
            hashtags = trends.get("hashtags", [])
            sounds = trends.get("sounds", [])
            if hashtags:
                top_tags = ", ".join(f"#{h['name']}" for h in hashtags[:10])
                trend_section += f"\n=== TRENDING HASHTAGS (TikTok) ===\n{top_tags}\nInclude 2-3 relevant trending hashtags in each script.\n"
            if sounds:
                top_sounds = ", ".join(f"\"{s['title']}\" by {s['author']}" for s in sounds[:5])
                trend_section += f"\n=== TRENDING SOUNDS ===\n{top_sounds}\n"

        # History section — avoid duplicate content
        history = self._load_history()
        history_section = ""
        if history:
            recent = history[-20:]  # last 20 scripts
            past_titles = [h.get("title", "") for h in recent]
            past_angles = [h.get("angle", "") for h in recent]
            history_section = f"""
=== PREVIOUSLY GENERATED (DO NOT REPEAT) ===
Past titles: {json.dumps(past_titles, ensure_ascii=False)}
Past angles: {json.dumps(past_angles, ensure_ascii=False)}
Create COMPLETELY DIFFERENT content from the above.
"""

        niche_hint = f"\n- Content niche/topic: {niche}" if niche else ""

        prompt = SCRIPT_PROMPT.format(
            video_count=video_count, content=content[:5000],
            language_name=language_name,
            competitor_section=competitor_section,
            trend_section=trend_section,
            history_section=history_section,
            niche_hint=niche_hint,
        )

        llm = get_llm_client()
        scripts = llm.generate_json(prompt)

        if isinstance(scripts, dict) and "scripts" in scripts:
            scripts = scripts["scripts"]
        if not isinstance(scripts, list):
            scripts = [scripts]

        # Save scripts
        scripts_path = job_dir / "scripts.json"
        with open(scripts_path, "w", encoding="utf-8") as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)

        # Update history to prevent future duplicates
        self._save_history(scripts, context.get("source_url", ""))

        logger.info(f"Generated {len(scripts)} unique scripts")
        return {
            "scripts": scripts,
            "scripts_path": str(scripts_path),
            "scripts_count": len(scripts),
        }

    def _extract_text(self, data: Dict) -> str:
        parts = []
        for key in ("title", "description", "body_text", "transcript"):
            if data.get(key):
                parts.append(f"{key.title()}: {data[key]}")
        return "\n\n".join(parts)

    def _load_history(self) -> List[Dict]:
        """Load script generation history"""
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_history(self, scripts: List[Dict], source_url: str):
        """Save generated scripts to history for deduplication"""
        try:
            history = self._load_history()
            for s in scripts:
                history.append({
                    "title": s.get("title", ""),
                    "angle": s.get("angle", ""),
                    "hook": s.get("hook", ""),
                    "source": source_url,
                })
            # Keep last 100 entries
            history = history[-100:]
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save history: {e}")
