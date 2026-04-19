"""
Base Agent — Clean base class for all pipeline agents.
Supports config injection, typed context, retry logic.
"""

import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .schemas import AgentStatus


class BaseAgent:
    """
    Base class cho tất cả agents.

    Subclass cần override:
        - execute(context: dict) -> dict
    """

    name: str = "BaseAgent"
    description: str = ""
    max_retries: int = 3
    retry_delay: float = 2.0
    is_critical: bool = True  # If True, pipeline stops on failure

    def __init__(self, config=None):
        """
        Args:
            config: Settings instance (injected, not imported)
        """
        self.config = config
        self.logger = logging.getLogger(f"agent.{self.name}")
        self.status = AgentStatus.IDLE
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.result: Optional[Dict] = None

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run agent with retry logic."""
        self.status = AgentStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self.error = None

        self.logger.info(f"▶ {self.name} started")

        for attempt in range(1, self.max_retries + 1):
            try:
                result = self.execute(context)

                self.status = AgentStatus.SUCCESS
                self.result = result
                self.finished_at = datetime.now(timezone.utc)

                elapsed = (self.finished_at - self.started_at).total_seconds()
                self.logger.info(f"✅ {self.name} completed in {elapsed:.1f}s")

                if result and isinstance(result, dict):
                    context.update(result)

                return context

            except Exception as e:
                self.error = str(e)
                self.logger.warning(
                    f"⚠ {self.name} attempt {attempt}/{self.max_retries} failed: {e}"
                )

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    self.logger.info(f"  Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    self.status = AgentStatus.FAILED
                    self.finished_at = datetime.now(timezone.utc)
                    self.logger.error(
                        f"❌ {self.name} failed after {self.max_retries} attempts: {e}\n"
                        f"{traceback.format_exc()}"
                    )
                    raise

        return context

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Override this — main agent logic."""
        raise NotImplementedError(f"{self.name}.execute() not implemented")

    def skip(self, reason: str = ""):
        """Mark agent as skipped"""
        self.status = AgentStatus.SKIPPED
        self.logger.info(f"⏭ {self.name} skipped{f' ({reason})' if reason else ''}")

    def get_status_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "elapsed_seconds": (
                (self.finished_at - self.started_at).total_seconds()
                if self.started_at and self.finished_at
                else None
            ),
        }

    def __repr__(self):
        return f"<{self.name} status={self.status.value}>"
