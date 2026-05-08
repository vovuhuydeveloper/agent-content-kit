"""
VideoQualityAgent — AI-powered video quality assessment with frame sampling.

Extracts sample frames from rendered videos and scores them using LLM vision
(or text heuristics as fallback). Low-scoring videos trigger scene regeneration.

Scoring criteria:
  - Visual appeal (composition, color, lighting)
  - Text readability (captions clear, not clipped)
  - Content relevance (matches script topic)
  - Production quality (no artifacts, smooth transitions)

Non-critical agent — pipeline publishes regardless if LLM unavailable.
"""

import base64
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent

logger = logging.getLogger("agent.video_quality")

QUALITY_PROMPT = """You are a TikTok/Shorts video quality reviewer.
Analyze these video frames and score the visual quality.

Scoring criteria (1-10 each):
1. Visual Appeal: Is the composition engaging? Colors vibrant? Would it stop a scroll?
2. Text Readability: Are captions clear, well-positioned, not clipped or overlapping?
3. Content Relevance: Does the visual match the video topic?
4. Production Quality: Any artifacts, blur, or awkward transitions?

=== VIDEO INFO ===
Title: {title}
Topic/Niche: {niche}
Scene description: {scene_text}

=== OUTPUT FORMAT (JSON only) ===
{{
    "visual_appeal": 8,
    "text_readability": 7,
    "content_relevance": 8,
    "production_quality": 7,
    "overall_score": 7.5,
    "is_acceptable": true,
    "feedback": "Good visual composition. Text is readable.",
    "regenerate_scenes": [],
    "suggestions": "Try brighter colors for more engagement."
}}

Return ONLY valid JSON. Overall score < 6.0 means NOT acceptable."""


class VideoQualityAgent(BaseAgent):
    name = "VideoQualityAgent"
    description = "AI video quality assessment with frame sampling and regeneration triggers"
    is_critical = False  # Non-critical — pipeline publishes even if quality check fails
    max_retries = 1

    # Quality thresholds
    MIN_ACCEPTABLE_SCORE = 5.5  # Overall score below this triggers regeneration
    MAX_REGENERATIONS = 3       # Prevent infinite loops

    def __init__(self, config=None):
        super().__init__(config)
        self._regeneration_count = 0

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        videos = context.get("videos", [])
        scripts = context.get("scripts", [])
        job_dir = Path(context["job_dir"])
        niche = context.get("niche", "")

        self._regeneration_count = context.get("quality_regeneration_count", 0)

        if self._regeneration_count >= self.MAX_REGENERATIONS:
            logger.warning(
                f"Max regenerations reached ({self.MAX_REGENERATIONS}) — "
                f"publishing as-is"
            )
            return {
                "quality_scores": [],
                "quality_overall": 6.0,
                "needs_regeneration": False,
                "quality_regeneration_count": self._regeneration_count,
            }

        quality_dir = job_dir / "quality_frames"
        quality_dir.mkdir(exist_ok=True)

        scores = []
        needs_regeneration = False
        regenerate_scenes = []

        for video in videos:
            script_id = video.get("script_id", 1)
            video_path = video.get("path", "")

            if not video_path or not Path(video_path).exists():
                continue

            # Extract sample frames
            frame_paths = self._extract_frames(
                video_path, quality_dir, script_id, n_frames=3
            )

            # Find matching script
            script = next(
                (s for s in scripts if s.get("script_id") == script_id), {}
            )

            # Score the video
            score = self._score_video(
                frame_paths=frame_paths,
                script=script,
                niche=niche,
            )
            score["script_id"] = script_id
            score["video_path"] = video_path
            scores.append(score)

            if not score.get("is_acceptable", True):
                needs_regeneration = True
                regenerate_scenes.extend(score.get("regenerate_scenes", []))
                logger.warning(
                    f"Video {script_id} quality LOW ({score.get('overall_score', '?')}/10) — "
                    f"marking for regeneration"
                )
            else:
                logger.info(
                    f"Video {script_id} quality OK ({score.get('overall_score', '?')}/10)"
                )

        # Save scores
        scores_path = job_dir / "quality_scores.json"
        with open(scores_path, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)

        overall = (
            sum(s.get("overall_score", 6) for s in scores) / len(scores)
            if scores else 6.0
        )

        if needs_regeneration:
            self._regeneration_count += 1

        return {
            "quality_scores": scores,
            "quality_overall": round(overall, 1),
            "needs_regeneration": needs_regeneration,
            "regenerate_scenes": regenerate_scenes,
            "quality_regeneration_count": self._regeneration_count,
        }

    def _extract_frames(
        self, video_path: str, output_dir: Path, script_id: int, n_frames: int = 3
    ) -> List[str]:
        """Extract sample frames from video using ffmpeg"""
        frames = []

        # Get video duration
        try:
            r = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path,
                ],
                capture_output=True, text=True, timeout=10,
            )
            duration = float(r.stdout.strip())
        except Exception:
            duration = 30.0

        # Extract frames at 25%, 50%, 75% of video
        for i in range(n_frames):
            timestamp = duration * (i + 1) / (n_frames + 1)
            frame_path = output_dir / f"v{script_id}_frame{i}.jpg"

            try:
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-ss", f"{timestamp:.1f}",
                        "-i", video_path, "-vframes", "1",
                        "-q:v", "2", str(frame_path),
                    ],
                    capture_output=True, timeout=30,
                )
                if frame_path.exists():
                    frames.append(str(frame_path))
            except Exception as e:
                logger.warning(f"Frame extraction failed at {timestamp}s: {e}")

        return frames

    def _score_video(
        self,
        frame_paths: List[str],
        script: Dict,
        niche: str,
    ) -> Dict[str, Any]:
        """Score video quality using LLM vision or heuristics"""
        if not frame_paths:
            return self._heuristic_score(script)

        try:
            from .llm_client import get_llm_client

            llm = get_llm_client()

            # Build prompt
            title = script.get("title", "Untitled")
            scene_text = script.get("hook", "") or " ".join(
                s.get("text", "") for s in script.get("scenes", [])[:2]
            )

            prompt = QUALITY_PROMPT.format(
                title=title,
                niche=niche,
                scene_text=scene_text[:500],
            )

            # Try vision-enabled call if frames available
            score = self._call_llm_vision(llm, prompt, frame_paths)

            if score:
                return score

        except Exception as e:
            logger.warning(f"LLM quality scoring failed: {e}")

        return self._heuristic_score(script)

    def _call_llm_vision(
        self, llm, prompt: str, frame_paths: List[str]
    ) -> Optional[Dict]:
        """Call LLM with frame images for vision-based scoring"""
        try:
            # Encode frames as base64
            images_b64 = []
            for fp in frame_paths[:2]:  # Max 2 frames to avoid large payload
                with open(fp, "rb") as f:
                    images_b64.append(base64.b64encode(f.read()).decode())

            # Try vision API if available
            if hasattr(llm, "generate_with_images"):
                result = llm.generate_with_images(
                    prompt=prompt,
                    images=images_b64,
                    response_format="json",
                )
                if isinstance(result, dict):
                    return self._normalize_score(result)
                if isinstance(result, str):
                    return self._normalize_score(json.loads(result))

            # Fallback: text-only with frame existence noted
            if hasattr(llm, "generate_json"):
                text_prompt = (
                    f"{prompt}\n\n"
                    f"(Note: {len(frame_paths)} video frames were extracted "
                    f"but vision analysis is unavailable. Score based on "
                    f"the scene description above.)"
                )
                result = llm.generate_json(text_prompt)
                if isinstance(result, dict):
                    return self._normalize_score(result)

        except Exception as e:
            logger.debug(f"Vision scoring failed: {e}")

        return None

    def _normalize_score(self, data: Dict) -> Dict:
        """Ensure score dict has all required fields"""
        overall = float(data.get("overall_score", 6))
        return {
            "visual_appeal": int(data.get("visual_appeal", 6)),
            "text_readability": int(data.get("text_readability", 6)),
            "content_relevance": int(data.get("content_relevance", 6)),
            "production_quality": int(data.get("production_quality", 6)),
            "overall_score": overall,
            "is_acceptable": overall >= self.MIN_ACCEPTABLE_SCORE,
            "feedback": data.get("feedback", ""),
            "regenerate_scenes": data.get("regenerate_scenes", []),
            "suggestions": data.get("suggestions", ""),
        }

    def _heuristic_score(self, script: Dict) -> Dict:
        """Fallback heuristic scoring when LLM unavailable"""
        hook = script.get("hook", "")
        scenes = script.get("scenes", [])
        cta = script.get("cta", "")

        # Basic heuristics
        score = 6.0

        # Bonus for having a hook
        if hook and len(hook) > 10:
            score += 0.5

        # Bonus for scene visual descriptions
        has_visuals = any(s.get("visual", "") for s in scenes)
        if has_visuals:
            score += 0.5

        # Bonus for CTA
        if cta:
            score += 0.5

        # Cap at 10
        score = min(10.0, score)

        return {
            "visual_appeal": 6,
            "text_readability": 7,
            "content_relevance": 6,
            "production_quality": 6,
            "overall_score": score,
            "is_acceptable": score >= self.MIN_ACCEPTABLE_SCORE,
            "feedback": "Heuristic score (LLM unavailable)",
            "regenerate_scenes": [],
            "suggestions": "",
        }
