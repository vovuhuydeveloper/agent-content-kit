"""
Pipeline — Orchestrator with checkpoint support.
Runs agents sequentially, saves state after each, supports resume.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent

logger = logging.getLogger("agent.pipeline")


class Pipeline:
    """
    Run agents sequentially with checkpoint/resume support.

    Usage:
        pipeline = Pipeline.default()
        result = pipeline.run(job_input)
    """

    def __init__(self, agents: Optional[List[BaseAgent]] = None):
        self.agents: List[BaseAgent] = agents or []
        self.status = "idle"
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None

    @classmethod
    def default(cls, config=None) -> "Pipeline":
        """Build default pipeline with all agents"""
        from .ab_testing import ABTestAgent
        from .analyzer import CompetitorAnalyzerAgent
        from .composer import VideoComposerAgent
        from .fetcher import ContentFetcherAgent
        from .publisher import PublisherAgent
        from .reviewer import QualityReviewAgent
        from .scriptwriter import ScriptWriterAgent
        from .thumbnail import ThumbnailAgent
        from .trend_scraper import TrendScraperAgent
        from .voice import VoiceGeneratorAgent

        agents = [
            ContentFetcherAgent(config),
            CompetitorAnalyzerAgent(config),
            TrendScraperAgent(config),        # Fetch TikTok trends
            ScriptWriterAgent(config),         # Uses trends + history for unique scripts
            ABTestAgent(config),
        ]

        # AI Video generation (Kling / Runway)
        # Auto-enable if KLING_API_KEY or RUNWAY_API_KEY is configured
        import os
        kling_key = os.getenv("KLING_API_KEY", "")
        runway_key = os.getenv("RUNWAY_API_KEY", "")
        if (kling_key and len(kling_key) > 10) or (runway_key and len(runway_key) > 10):
            from .ai_video import AIVideoAgent
            agents.append(AIVideoAgent(config))
            logger.info("🎬 AI Video generation (Kling/Runway) enabled")

        # Pixelle-Video AI image generation
        # Auto-enable if PIXELLE_ENABLED=true OR PIXELLE_VIDEO_API_URL is configured
        pixelle_enabled = os.getenv("PIXELLE_ENABLED", "false").lower() in (
            "true", "1", "yes"
        )
        pixelle_url = os.getenv("PIXELLE_VIDEO_API_URL", "")
        pixelle_configured = bool(
            pixelle_url
            and pixelle_url != "http://localhost:8085"
            and "://" in pixelle_url
        )
        if pixelle_enabled or pixelle_configured:
            from .ai_image import AIImageAgent
            agents.append(AIImageAgent(config))
            logger.info("🎨 Pixelle-Video AI image generation enabled")

        # Character agent (talking pet/avatar)
        from .character import CharacterAgent
        agents.append(CharacterAgent(config))

        agents.extend([
            VoiceGeneratorAgent(config),
            VideoComposerAgent(config),
            ThumbnailAgent(config),
            QualityReviewAgent(config),
            PublisherAgent(config),
        ])
        return cls(agents)

    def run(self, job_input: Dict[str, Any], resume_from: str = "") -> Dict[str, Any]:
        """
        Run the full pipeline.

        Args:
            job_input: Job parameters from API
            resume_from: Agent name to resume from (skip earlier agents)
        """
        self.status = "running"
        self.started_at = datetime.now(timezone.utc)

        context = self._init_context(job_input)

        # If resuming, load checkpoint
        if resume_from:
            context = self._load_checkpoint(context, resume_from)

        logger.info(f"{'=' * 60}")
        logger.info(f"🚀 Pipeline started — Job: {context['job_id']}")
        logger.info(f"   Source: {context['source_url']}")
        logger.info(f"   Platforms: {', '.join(context['platforms'])}")
        logger.info(f"{'=' * 60}")

        skip = bool(resume_from)

        for agent in self.agents:
            # Skip agents until we reach resume point
            if skip:
                if agent.name == resume_from:
                    skip = False
                else:
                    agent.skip("checkpoint resume")
                    context["agent_results"].append(agent.get_status_dict())
                    continue

            try:
                # Skip CompetitorAnalyzer if no URLs
                if agent.name == "CompetitorAnalyzerAgent" and not context.get("competitor_urls"):
                    agent.skip("no competitor URLs")
                    context["agent_results"].append(agent.get_status_dict())
                    continue

                # PAUSE before Publisher — wait for Telegram approval
                if agent.name == "PublisherAgent" and not resume_from:
                    logger.info("⏸ Pipeline paused — awaiting Telegram approval")
                    context["pipeline_status"] = "awaiting_approval"
                    context["last_checkpoint"] = "QualityReviewAgent"
                    self._save_checkpoint(context)

                    # Send Telegram notification
                    try:
                        from .notifier import TelegramNotifier
                        notifier = TelegramNotifier()
                        notifier.notify_video_ready(context)
                    except Exception as e:
                        logger.warning(f"Telegram notification failed: {e}")

                    self.status = "awaiting_approval"
                    self.finished_at = datetime.now(timezone.utc)
                    elapsed = (self.finished_at - self.started_at).total_seconds()
                    context["pipeline_elapsed_seconds"] = elapsed

                    logger.info(f"{'=' * 60}")
                    logger.info(f"⏸ Pipeline paused after {elapsed:.1f}s — waiting for approval")
                    logger.info(f"{'=' * 60}")
                    return context

                context = agent.run(context)
                context["agent_results"].append(agent.get_status_dict())

                # Save checkpoint after success
                context["last_checkpoint"] = agent.name
                self._save_checkpoint(context)

            except Exception as e:
                logger.error(f"💥 Pipeline stopped at {agent.name}: {e}")
                context["errors"].append({"agent": agent.name, "error": str(e)})
                context["agent_results"].append(agent.get_status_dict())

                if agent.is_critical:
                    self.status = "failed"
                    self.finished_at = datetime.now(timezone.utc)
                    context["pipeline_status"] = "failed"
                    self._save_checkpoint(context)
                    return context

                logger.warning("  ↳ Continuing (non-critical)")

        self.status = "completed"
        self.finished_at = datetime.now(timezone.utc)
        elapsed = (self.finished_at - self.started_at).total_seconds()

        context["pipeline_status"] = "completed"
        context["pipeline_elapsed_seconds"] = elapsed

        logger.info(f"{'=' * 60}")
        logger.info(f"🎉 Pipeline completed in {elapsed:.1f}s")
        logger.info(f"{'=' * 60}")

        return context

    def _init_context(self, job_input: Dict) -> Dict[str, Any]:
        """Initialize pipeline context from job input"""
        job_id = job_input.get("job_id", f"job_{int(time.time())}")

        # Create job directory
        job_dir = Path(f"data/jobs/{job_id}")
        job_dir.mkdir(parents=True, exist_ok=True)

        return {
            "job_id": job_id,
            "job_input": job_input,
            "job_dir": str(job_dir),
            "source_url": job_input["source_url"],
            "character_images": job_input.get("character_images", []),
            "competitor_urls": job_input.get("competitor_urls", []),
            "platforms": job_input.get("platforms", ["tiktok"]),
            "language": job_input.get("language", "vi"),
            "video_count": job_input.get("video_count", 1),
            "niche": job_input.get("niche", ""),
            "character_mode": job_input.get("character_mode", "static"),
            "agent_results": [],
            "errors": [],
            "last_checkpoint": "",
        }

    def _save_checkpoint(self, context: Dict):
        """Save pipeline state to disk for resume"""
        try:
            job_dir = Path(context["job_dir"])
            checkpoint_path = job_dir / "checkpoint.json"

            # Save serializable subset
            save_data = {
                k: v for k, v in context.items()
                if isinstance(v, (str, int, float, bool, list, dict, type(None)))
            }
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Checkpoint save failed: {e}")

    def _load_checkpoint(self, context: Dict, resume_from: str) -> Dict:
        """Load checkpoint from disk"""
        try:
            job_dir = Path(context["job_dir"])
            checkpoint_path = job_dir / "checkpoint.json"
            if checkpoint_path.exists():
                with open(checkpoint_path, "r") as f:
                    saved = json.load(f)
                # Merge saved data into context
                context.update(saved)
                context["agent_results"] = []  # Reset for new run
                context["errors"] = []
                logger.info(f"Resumed from checkpoint: {resume_from}")
        except Exception as e:
            logger.warning(f"Checkpoint load failed: {e}")
        return context

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "agents": [a.get_status_dict() for a in self.agents],
        }