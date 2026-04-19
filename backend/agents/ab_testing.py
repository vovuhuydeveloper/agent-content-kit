"""
ABTestAgent — Generate multiple script variants for A/B testing.
Creates 2-3 variants with different hooks, CTAs, and pacing.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from .base import BaseAgent
from .llm_client import get_llm_client

logger = logging.getLogger("agent.ab_testing")

AB_PROMPT = """You are an A/B testing specialist for short-form video content.

Given the following video script, create {variant_count} VARIANTS with different approaches.

=== ORIGINAL SCRIPT ===
Title: {title}
Hook: {hook}
Scenes: {scenes}
CTA: {cta}

=== VARIANT STRATEGIES ===
- Variant A: Original script (keep as-is)
- Variant B: Different hook style (question-based, shocking stat, or story-based)
- Variant C: Different CTA (urgency-based, curiosity-based, or social-proof)

=== OUTPUT FORMAT (JSON array) ===
[
  {{
    "variant": "A",
    "variant_label": "Original",
    "title": "...",
    "hook": "...",
    "scenes": [...],
    "cta": "...",
    "hypothesis": "Control group - original script"
  }},
  {{
    "variant": "B",
    "variant_label": "Question Hook",
    "title": "...",
    "hook": "Different hook approach...",
    "scenes": [...],
    "cta": "...",
    "hypothesis": "Question-based hooks may increase watch time"
  }}
]

Return ONLY valid JSON.
"""


class ABTestAgent(BaseAgent):
    """Generate A/B test variants of scripts"""
    name = "ABTestAgent"
    description = "Generate A/B test variants for scripts"
    is_critical = False  # Non-critical — pipeline continues if this fails

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        scripts = context.get("scripts", [])
        job_dir = Path(context["job_dir"])
        variant_count = context.get("ab_variant_count", 2)

        if not scripts:
            logger.warning("No scripts to create variants for")
            return {"ab_variants": [], "ab_testing_enabled": False}

        all_variants = []

        for script in scripts:
            script_id = script.get("script_id", 1)
            title = script.get("title", "")
            hook = script.get("hook", "")
            scenes = json.dumps(script.get("scenes", []), ensure_ascii=False)[:1500]
            cta = script.get("cta", "")

            prompt = AB_PROMPT.format(
                variant_count=variant_count,
                title=title,
                hook=hook,
                scenes=scenes,
                cta=cta,
            )

            try:
                llm = get_llm_client()
                variants = llm.generate_json(prompt)

                if isinstance(variants, dict):
                    variants = variants.get("variants", [variants])
                if not isinstance(variants, list):
                    variants = [variants]

                # Tag each variant with script_id
                for v in variants:
                    v["script_id"] = script_id

                all_variants.extend(variants)
                logger.info(f"Generated {len(variants)} A/B variants for script {script_id}")

            except Exception as e:
                logger.warning(f"A/B variant generation failed for script {script_id}: {e}")
                # Fallback: use original as variant A
                all_variants.append({
                    "script_id": script_id,
                    "variant": "A",
                    "variant_label": "Original",
                    "title": title,
                    "hook": hook,
                    "cta": cta,
                    "hypothesis": "Control",
                })

        # Save
        ab_path = job_dir / "ab_variants.json"
        with open(ab_path, "w", encoding="utf-8") as f:
            json.dump(all_variants, f, ensure_ascii=False, indent=2)

        return {
            "ab_variants": all_variants,
            "ab_variant_count": len(all_variants),
            "ab_testing_enabled": True,
        }
