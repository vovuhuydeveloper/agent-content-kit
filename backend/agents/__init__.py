"""
Content Agent System — Clean architecture.

Usage:
    from backend.agents import Pipeline
    pipeline = Pipeline.default()
    result = pipeline.run(job_input)
"""

from .base import BaseAgent
from .pipeline import Pipeline
from .schemas import AgentStatus, JobInput, PipelineContext

__all__ = [
    "BaseAgent",
    "AgentStatus",
    "Pipeline",
    "PipelineContext",
    "JobInput",
]
