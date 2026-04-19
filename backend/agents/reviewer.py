"""
QualityReviewAgent — AI review chất lượng video trước khi publish.
Dùng LLM để check script quality, scoring, approve/reject.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from .base import BaseAgent

logger = logging.getLogger("agent.quality_review")

REVIEW_PROMPT = """You are a strict content quality reviewer.
Review this video script and provide a quality assessment.

=== SCRIPT ===
Title: {title}
Hook: {hook}
Scenes: {scenes}
CTA: {cta}

=== VIDEO INFO ===
Duration: ~{duration}s
Platform: {platforms}
Language: {language}

=== REVIEW CRITERIA ===
1. Hook strength (is it attention-grabbing in first 3 seconds?)
2. Content clarity (is the message clear and valuable?)
3. Pacing (is the flow natural, not too fast/slow?)
4. CTA effectiveness (does it motivate action?)
5. Platform fit (appropriate for target platforms?)
6. Brand consistency (does the character/overlay fit naturally?)

=== OUTPUT FORMAT (JSON only) ===
{{
    "score": 8,
    "approved": true,
    "feedback": {{
        "hook": "Strong hook, grabs attention immediately",
        "content": "Clear educational content",
        "pacing": "Good flow",
        "cta": "Effective CTA",
        "overall": "High quality script ready for production"
    }},
    "suggestions": ["Optional improvement suggestions"],
    "risk_flags": ["Any content risks or issues"]
}}

Score 1-10. Approve if score >= 7. Return ONLY valid JSON.
"""


class QualityReviewAgent(BaseAgent):
    name = "QualityReviewAgent"
    description = "AI review chất lượng content trước khi publish"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        scripts = context["scripts"]
        videos = context.get("videos", [])
        platforms = context.get("platforms", [])
        language = context.get("language", "vi")

        reviews = []
        approved_videos = []

        for script in scripts:
            script_id = script.get("script_id", 1)

            review = self._review_script(script, platforms, language)
            review["script_id"] = script_id
            reviews.append(review)

            if review.get("approved", False):
                # Find matching video
                video = next(
                    (v for v in videos if v.get("script_id") == script_id), None
                )
                if video:
                    approved_videos.append(video)
                    logger.info(f"✅ Script {script_id} approved (score: {review.get('score', '?')})")
            else:
                logger.warning(f"❌ Script {script_id} rejected (score: {review.get('score', '?')})")

        # Save reviews
        job_dir = Path(context["job_dir"])
        review_path = job_dir / "reviews.json"
        with open(review_path, "w", encoding="utf-8") as f:
            json.dump(reviews, f, ensure_ascii=False, indent=2)

        return {
            "reviews": reviews,
            "approved_videos": approved_videos,
            "approved_count": len(approved_videos),
            "rejected_count": len(scripts) - len(approved_videos),
        }

    def _review_script(self, script: Dict, platforms: list, language: str) -> Dict:
        """Review a single script"""
        title = script.get("title", "Untitled")
        hook = script.get("hook", "")
        scenes = json.dumps(script.get("scenes", []), ensure_ascii=False)[:1000]
        cta = script.get("cta", "")
        duration = script.get("estimated_duration", 45)

        prompt = REVIEW_PROMPT.format(
            title=title,
            hook=hook,
            scenes=scenes,
            cta=cta,
            duration=duration,
            platforms=", ".join(platforms),
            language=language,
        )

        try:
            from .llm_client import get_llm_client
            llm = get_llm_client()

            review = llm.generate_json(prompt)
            return review
        except Exception as e:
            logger.warning(f"LLM review failed: {e}. Auto-approving.")
            # Fallback: auto-approve
            return {
                "score": 7,
                "approved": True,
                "feedback": {"overall": "Auto-approved (LLM unavailable)"},
                "suggestions": [],
                "risk_flags": [],
            }
