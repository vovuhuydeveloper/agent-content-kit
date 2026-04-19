"""
Pydantic schemas cho Agent Pipeline.
Typed models thay thế raw dict — validate I/O giữa agents.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ──────────────────────────────
# Enums
# ──────────────────────────────

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class Platform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class CharacterPose(str, Enum):
    STANDING = "standing"
    EXPLAINING = "explaining"
    TEACHING = "teaching"
    WAVING = "waving"
    QUESTIONING = "questioning"
    CELEBRATING = "celebrating"
    SURPRISED = "surprised"
    THUMBSUP = "thumbsup"


# ──────────────────────────────
# Job Input (from API)
# ──────────────────────────────

class JobInput(BaseModel):
    """Input từ user qua API endpoint"""
    job_id: str
    source_url: str
    language: str = "vi"
    video_count: int = 1
    platforms: List[str] = Field(default_factory=lambda: ["tiktok"])
    niche: str = ""
    character_images: List[str] = Field(default_factory=list)
    competitor_urls: List[str] = Field(default_factory=list)


# ──────────────────────────────
# Content Fetcher
# ──────────────────────────────

class ContentData(BaseModel):
    """Output từ ContentFetcherAgent"""
    source_url: str
    source_type: str = "webpage"  # webpage | youtube | tiktok
    title: str = ""
    description: str = ""
    body_text: str = ""
    transcript: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ──────────────────────────────
# Script Writer
# ──────────────────────────────

class ScriptScene(BaseModel):
    """1 scene trong script"""
    scene_id: int = 1
    text: str
    duration: int = 5
    visual: str = ""  # mô tả visual để search stock footage
    character_pose: CharacterPose = CharacterPose.EXPLAINING


class Script(BaseModel):
    """1 complete script cho 1 video"""
    script_id: int = 1
    title: str = ""
    hook: str = ""  # opening hook
    scenes: List[ScriptScene] = Field(default_factory=list)
    cta: str = ""  # call to action
    hashtags: List[str] = Field(default_factory=list)
    estimated_duration: int = 45
    platform_notes: Dict[str, str] = Field(default_factory=dict)


# ──────────────────────────────
# Voice Generator
# ──────────────────────────────

class VoiceFile(BaseModel):
    """Output từ VoiceGeneratorAgent"""
    script_id: int
    path: str
    duration: float = 0.0
    voice_name: str = ""
    provider: str = "edge-tts"  # edge-tts | elevenlabs


# ──────────────────────────────
# Video Composer
# ──────────────────────────────

class VideoOutput(BaseModel):
    """Output từ VideoComposerAgent"""
    script_id: int
    path: str
    title: str = ""
    file_size: int = 0
    orientation: str = "vertical"
    width: int = 1080
    height: int = 1920


# ──────────────────────────────
# Thumbnail
# ──────────────────────────────

class ThumbnailOutput(BaseModel):
    """Output từ ThumbnailAgent"""
    script_id: int
    path: str


# ──────────────────────────────
# Quality Review
# ──────────────────────────────

class ReviewResult(BaseModel):
    """Output từ QualityReviewAgent"""
    script_id: int
    score: int = 0
    approved: bool = False
    feedback: str = ""
    suggestions: List[str] = Field(default_factory=list)


# ──────────────────────────────
# Publisher
# ──────────────────────────────

class PublicationResult(BaseModel):
    """Output từ PublisherAgent"""
    script_id: int
    platform: str
    status: str = "draft"  # draft | published | failed
    url: str = ""
    error: str = ""


# ──────────────────────────────
# Agent Status (for tracking)
# ──────────────────────────────

class AgentResult(BaseModel):
    """Status/result of a single agent run"""
    agent: str
    status: AgentStatus
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    error: Optional[str] = None


# ──────────────────────────────
# Pipeline Context (master state)
# ──────────────────────────────

class PipelineContext(BaseModel):
    """
    Typed context thay thế raw dict.
    Được pass qua tất cả agents trong pipeline.
    """
    # Job metadata
    job_id: str
    job_input: JobInput
    job_dir: str = ""

    # Source
    source_url: str
    language: str = "vi"
    video_count: int = 1
    platforms: List[str] = Field(default_factory=lambda: ["tiktok"])
    niche: str = ""

    # Character
    character_images: List[str] = Field(default_factory=list)
    competitor_urls: List[str] = Field(default_factory=list)

    # Agent outputs (filled progressively)
    content_data: Optional[ContentData] = None
    competitor_insights: Optional[Dict[str, Any]] = None
    scripts: List[Script] = Field(default_factory=list)
    voice_files: List[VoiceFile] = Field(default_factory=list)
    videos: List[VideoOutput] = Field(default_factory=list)
    thumbnails: List[ThumbnailOutput] = Field(default_factory=list)
    reviews: List[ReviewResult] = Field(default_factory=list)
    publications: List[PublicationResult] = Field(default_factory=list)

    # Pipeline tracking
    agent_results: List[AgentResult] = Field(default_factory=list)
    errors: List[Dict[str, str]] = Field(default_factory=list)
    pipeline_status: str = "pending"
    pipeline_elapsed_seconds: float = 0.0

    # Checkpoint (for resume)
    last_checkpoint: str = ""

    class Config:
        arbitrary_types_allowed = True
