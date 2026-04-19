"""
ContentJob model — Theo dõi mỗi job request từ user.
"""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text

from backend.models.base import BaseModel


class ContentJob(BaseModel):
    """Mỗi job = 1 lần user submit link → pipeline chạy"""

    __tablename__ = "content_jobs"

    # Input
    source_url = Column(String(2048), nullable=False, comment="URL nguồn content")
    source_type = Column(String(20), default="web", comment="web|video")
    language = Column(String(10), default="vi", comment="vi|en")
    niche = Column(String(200), default="", comment="Chủ đề/niche")
    video_count = Column(Integer, default=3, comment="Số video cần tạo")
    platforms = Column(JSON, default=list, comment="Target platforms")
    competitor_urls = Column(JSON, default=list, comment="Competitor URLs")
    character_images = Column(JSON, default=list, comment="Character image paths")

    # Status
    status = Column(
        String(20), default="pending",
        comment="pending|running|completed|failed"
    )
    current_agent = Column(String(50), default="", comment="Agent đang chạy")
    progress = Column(Float, default=0.0, comment="Progress 0-100%")

    # Results
    scripts_count = Column(Integer, default=0)
    videos_count = Column(Integer, default=0)
    published_count = Column(Integer, default=0)

    # Pipeline data
    pipeline_result = Column(JSON, default=dict, comment="Full pipeline result")
    error_message = Column(Text, default="")

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    elapsed_seconds = Column(Float, default=0.0)
